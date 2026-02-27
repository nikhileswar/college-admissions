import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import transaction

from .models import Branch, StudentProfile, Preference, MatchingResult, Allotment
from .forms import StudentSignupForm, StudentLoginForm, BranchForm, AdminStudentForm, AdminStudentRankForm
from .algorithm import run_gale_shapley

User = get_user_model()


def is_admin(user):
    return user.is_staff or user.is_superuser


def is_student(user):
    return user.is_authenticated and not user.is_staff and hasattr(user, 'profile')


# ─────────────────────────────────────────────────────────────
# AUTH VIEWS
# ─────────────────────────────────────────────────────────────

def login_view(request):
    """Combined login page with student signup tab."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    signup_form = StudentSignupForm()
    login_form = StudentLoginForm()
    active_tab = 'login'

    if request.method == 'POST':
        action = request.POST.get('action', 'login')

        if action == 'signup':
            active_tab = 'signup'
            signup_form = StudentSignupForm(request.POST)
            if signup_form.is_valid():
                user, profile = signup_form.save()
                login(request, user)
                messages.success(request, f'Welcome, {profile.display_name()}! Your account has been created.')
                return redirect('student_preferences')
            # form errors will be shown in template

        elif action == 'student_login':
            active_tab = 'login'
            login_form = StudentLoginForm(request, data=request.POST)
            if login_form.is_valid():
                user = login_form.get_user()
                if user.is_staff:
                    messages.error(request, 'Admin users must use the Admin Login tab.')
                elif not hasattr(user, 'profile'):
                    messages.error(request, 'No student profile found for this account.')
                else:
                    login(request, user)
                    return redirect('student_preferences')
            else:
                messages.error(request, 'Invalid username or password.')

        elif action == 'admin_login':
            active_tab = 'admin'
            username = request.POST.get('username', '').strip()
            password = request.POST.get('password', '')
            user = authenticate(request, username=username, password=password)
            if user and user.is_staff:
                login(request, user)
                return redirect('admin_setup')
            else:
                messages.error(request, 'Invalid admin credentials.')

    return render(request, 'matching/login.html', {
        'signup_form': signup_form,
        'login_form': login_form,
        'active_tab': active_tab,
    })


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def dashboard(request):
    """Route to the right portal based on role."""
    if request.user.is_staff:
        return redirect('admin_setup')
    return redirect('student_preferences')


# ─────────────────────────────────────────────────────────────
# ADMIN VIEWS
# ─────────────────────────────────────────────────────────────

@login_required
@user_passes_test(is_admin, login_url='/login/')
def admin_setup(request):
    """Admin: manage branches and students."""
    branch_form = BranchForm()
    student_form = AdminStudentForm(initial={'password': 'jee2025'})

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_branch':
            branch_form = BranchForm(request.POST)
            if branch_form.is_valid():
                new_branch = branch_form.save()
                # Add to end of all existing students' pref lists
                for profile in StudentProfile.objects.all():
                    max_rank = profile.preferences.count()
                    Preference.objects.get_or_create(
                        student=profile, branch=new_branch,
                        defaults={'rank': max_rank + 1}
                    )
                messages.success(request, f'Branch "{new_branch}" added.')
                return redirect('admin_setup')
            else:
                messages.error(request, 'Please fix the errors below.')

        elif action == 'delete_branch':
            bid = request.POST.get('branch_id')
            branch = get_object_or_404(Branch, id=bid)
            name = str(branch)
            branch.delete()
            messages.success(request, f'Branch "{name}" deleted.')
            return redirect('admin_setup')

        elif action == 'add_student':
            student_form = AdminStudentForm(request.POST)
            if student_form.is_valid():
                user, profile = student_form.save()
                messages.success(request, f'Student "{profile.display_name()}" added with password "{student_form.cleaned_data["password"]}".')
                return redirect('admin_setup')
            else:
                messages.error(request, 'Fix the student form errors.')

        elif action == 'delete_student':
            sid = request.POST.get('student_id')
            profile = get_object_or_404(StudentProfile, id=sid)
            name = profile.display_name()
            profile.user.delete()
            messages.success(request, f'Student "{name}" deleted.')
            return redirect('admin_setup')

        elif action == 'load_demo':
            _load_demo_data()
            messages.success(request, '✅ JEE Advanced 2025 demo data loaded! 200 students across all 23 IITs.')
            return redirect('admin_setup')

        elif action == 'reset_all':
            MatchingResult.objects.all().delete()
            StudentProfile.objects.all().delete()
            User.objects.filter(is_staff=False, is_superuser=False).delete()
            Branch.objects.all().delete()
            messages.success(request, 'All data has been reset.')
            return redirect('admin_setup')

    branches = Branch.objects.all()
    students = StudentProfile.objects.select_related('user').order_by('air_rank')
    submitted_count = students.filter(has_submitted=True).count()
    total_seats = sum(b.seats for b in branches)

    return render(request, 'matching/admin_setup.html', {
        'branches': branches,
        'students': students,
        'branch_form': branch_form,
        'student_form': student_form,
        'submitted_count': submitted_count,
        'total_seats': total_seats,
    })


@login_required
@user_passes_test(is_admin, login_url='/login/')
def admin_preferences(request):
    """Admin: view all students' preference submissions."""
    q = request.GET.get('q', '').strip()
    students = StudentProfile.objects.select_related('user').order_by('air_rank')
    if q:
        students = students.filter(
            user__first_name__icontains=q
        ) | StudentProfile.objects.filter(
            user__last_name__icontains=q
        ) | StudentProfile.objects.filter(
            user__username__icontains=q
        )
        students = students.distinct().order_by('air_rank')

    student_data = []
    for profile in students:
        top5 = profile.preferences.order_by('rank').select_related('branch')[:5]
        student_data.append({
            'profile': profile,
            'top5': top5,
            'total_prefs': profile.preferences.count(),
        })

    submitted = StudentProfile.objects.filter(has_submitted=True).count()
    total = StudentProfile.objects.count()

    return render(request, 'matching/admin_preferences.html', {
        'student_data': student_data,
        'submitted': submitted,
        'total': total,
        'pending': total - submitted,
        'q': q,
    })


@login_required
@user_passes_test(is_admin, login_url='/login/')
def admin_student_ranks(request):
    """Admin: assign/update AIR rank for student profiles."""
    rank_form = AdminStudentRankForm()

    if request.method == 'POST' and request.POST.get('action') == 'save_rank':
        rank_form = AdminStudentRankForm(request.POST)
        if rank_form.is_valid():
            profile = rank_form.cleaned_data['student']
            profile.air_rank = rank_form.cleaned_data['air_rank']
            profile.save(update_fields=['air_rank'])
            messages.success(request, f'Updated AIR rank for "{profile.user.get_full_name() or profile.user.username}".')
            return redirect('admin_student_ranks')
        messages.error(request, 'Fix the rank form errors.')

    students = StudentProfile.objects.select_related('user').order_by('air_rank', 'user__first_name', 'user__username')
    return render(request, 'matching/admin_student_ranks.html', {
        'rank_form': rank_form,
        'students': students,
    })


@login_required
@user_passes_test(is_admin, login_url='/login/')
def admin_student_detail(request, student_id):
    """Admin: view full preference list for one student."""
    profile = get_object_or_404(StudentProfile, id=student_id)
    prefs = profile.preferences.order_by('rank').select_related('branch')
    return render(request, 'matching/admin_student_detail.html', {
        'profile': profile,
        'prefs': prefs,
    })


@login_required
@user_passes_test(is_admin, login_url='/login/')
def admin_results(request):
    """Admin: run matching and view results."""
    if request.method == 'POST' and request.POST.get('action') == 'run_matching':
        result = run_gale_shapley()
        if result:
            messages.success(request, f'✅ Stable matching complete! {result.total_matched} students matched.')
        else:
            messages.error(request, 'Add students and branches first.')
        return redirect('admin_results')

    result = MatchingResult.objects.filter(is_active=True).first()
    allotments_by_branch = {}
    unmatched = []

    if result:
        for allotment in result.allotments.select_related('student__user', 'branch').order_by('branch__college', 'branch__branch'):
            if allotment.is_matched and allotment.branch:
                key = allotment.branch.id
                if key not in allotments_by_branch:
                    allotments_by_branch[key] = {'branch': allotment.branch, 'allotments': []}
                allotments_by_branch[key]['allotments'].append(allotment)
            elif not allotment.is_matched:
                unmatched.append(allotment)

    branches = Branch.objects.all()
    branch_results = []
    for branch in branches:
        allots = allotments_by_branch.get(branch.id, {}).get('allotments', [])
        branch_results.append({
            'branch': branch,
            'allotments': allots,
            'filled': len(allots),
            'empty': branch.seats - len(allots),
        })

    return render(request, 'matching/admin_results.html', {
        'result': result,
        'branch_results': branch_results,
        'unmatched': unmatched,
    })


# ─────────────────────────────────────────────────────────────
# STUDENT VIEWS
# ─────────────────────────────────────────────────────────────

@login_required
def student_preferences(request):
    """Student: view and update their preference list."""
    if request.user.is_staff:
        return redirect('admin_setup')

    profile = get_object_or_404(StudentProfile, user=request.user)
    branches = Branch.objects.all()

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            ordered_ids = data.get('ordered_ids', [])
        except (json.JSONDecodeError, AttributeError):
            return JsonResponse({'error': 'Invalid data'}, status=400)

        if not ordered_ids:
            return JsonResponse({'error': 'Empty preference list'}, status=400)

        with transaction.atomic():
            Preference.objects.filter(student=profile).delete()
            prefs_to_create = []
            for rank, branch_id in enumerate(ordered_ids, start=1):
                try:
                    branch = Branch.objects.get(id=int(branch_id))
                    prefs_to_create.append(Preference(student=profile, branch=branch, rank=rank))
                except (Branch.DoesNotExist, ValueError):
                    continue
            Preference.objects.bulk_create(prefs_to_create)
            profile.has_submitted = True
            profile.save()

        return JsonResponse({'success': True, 'message': 'Preferences saved!'})

    # GET: build ordered pref list
    existing_prefs = list(
        profile.preferences.order_by('rank').select_related('branch')
    )
    existing_branch_ids = {p.branch_id for p in existing_prefs}

    # Append any branches not yet in their list (e.g. added after signup)
    extra_branches = [b for b in branches if b.id not in existing_branch_ids]
    ordered_branches = [p.branch for p in existing_prefs] + extra_branches

    return render(request, 'matching/student_preferences.html', {
        'profile': profile,
        'ordered_branches': ordered_branches,
        'total_branches': branches.count(),
    })


@login_required
def student_allotment(request):
    """Student: view their allotment result."""
    if request.user.is_staff:
        return redirect('admin_setup')

    profile = get_object_or_404(StudentProfile, user=request.user)
    result = MatchingResult.objects.filter(is_active=True).first()
    allotment = None

    if result:
        allotment = Allotment.objects.filter(result=result, student=profile).select_related('branch').first()

    top_prefs = profile.preferences.order_by('rank').select_related('branch')[:15]
    total_prefs = profile.preferences.count()

    return render(request, 'matching/student_allotment.html', {
        'profile': profile,
        'result': result,
        'allotment': allotment,
        'top_prefs': top_prefs,
        'total_prefs': total_prefs,
    })


# ─────────────────────────────────────────────────────────────
# DEMO DATA LOADER
# ─────────────────────────────────────────────────────────────

def _load_demo_data():
    """Load JEE Advanced 2025 demo: all 23 IITs + 200 students."""
    # Clear existing
    MatchingResult.objects.all().delete()
    StudentProfile.objects.all().delete()
    User.objects.filter(is_staff=False, is_superuser=False).delete()
    Branch.objects.all().delete()

    branches_data = [
        ('IIT Bombay', 'Computer Science & Engg', 5),
        ('IIT Bombay', 'Electrical Engineering', 5),
        ('IIT Bombay', 'Engineering Physics', 3),
        ('IIT Bombay', 'Mechanical Engineering', 4),
        ('IIT Bombay', 'Chemical Engineering', 3),
        ('IIT Delhi', 'Computer Science & Engg', 5),
        ('IIT Delhi', 'Electrical Engineering', 5),
        ('IIT Delhi', 'Mathematics & Computing', 4),
        ('IIT Delhi', 'Mechanical Engineering', 4),
        ('IIT Delhi', 'Chemical Engineering', 3),
        ('IIT Madras', 'Computer Science & Engg', 5),
        ('IIT Madras', 'AI & Data Analytics', 4),
        ('IIT Madras', 'Electrical Engineering', 5),
        ('IIT Madras', 'Mechanical Engineering', 4),
        ('IIT Kanpur', 'Computer Science & Engg', 5),
        ('IIT Kanpur', 'Electrical Engineering', 5),
        ('IIT Kanpur', 'Mathematics & Scientific Computing', 4),
        ('IIT Kanpur', 'Aerospace Engineering', 3),
        ('IIT Kharagpur', 'Computer Science & Engg', 5),
        ('IIT Kharagpur', 'Electronics & Electrical Comm.', 5),
        ('IIT Kharagpur', 'Mechanical Engineering', 4),
        ('IIT Kharagpur', 'Aerospace Engineering', 3),
        ('IIT Roorkee', 'Computer Science & Engg', 5),
        ('IIT Roorkee', 'Electronics & Comm. Engg', 5),
        ('IIT Roorkee', 'Electrical Engineering', 4),
        ('IIT Roorkee', 'Mechanical Engineering', 4),
        ('IIT Guwahati', 'Computer Science & Engg', 4),
        ('IIT Guwahati', 'Electronics & Comm. Engg', 4),
        ('IIT Guwahati', 'Mechanical Engineering', 3),
        ('IIT Hyderabad', 'Computer Science & Engg', 4),
        ('IIT Hyderabad', 'Artificial Intelligence', 4),
        ('IIT Hyderabad', 'Electrical Engineering', 3),
        ('IIT BHU Varanasi', 'Computer Science & Engg', 4),
        ('IIT BHU Varanasi', 'Electronics Engineering', 4),
        ('IIT BHU Varanasi', 'Mechanical Engineering', 3),
        ('IIT Indore', 'Computer Science & Engg', 4),
        ('IIT Indore', 'Electrical Engineering', 3),
        ('IIT Gandhinagar', 'Computer Science & Engg', 3),
        ('IIT Gandhinagar', 'Electrical Engineering', 3),
        ('IIT Jodhpur', 'Computer Science & Engg', 3),
        ('IIT Jodhpur', 'AI & Data Science', 3),
        ('IIT Mandi', 'Computer Science & Engg', 3),
        ('IIT Mandi', 'Electrical Engineering', 3),
        ('IIT Patna', 'Computer Science & Engg', 3),
        ('IIT Patna', 'Electronics & Comm. Engg', 3),
        ('IIT Tirupati', 'Computer Science & Engg', 3),
        ('IIT Tirupati', 'Electrical Engineering', 3),
        ('IIT Bhubaneswar', 'Computer Science & Engg', 3),
        ('IIT Bhubaneswar', 'Electrical Engineering', 3),
        ('IIT Ropar', 'Computer Science & Engg', 3),
        ('IIT Ropar', 'Artificial Intelligence', 3),
        ('IIT Palakkad', 'Computer Science & Engg', 3),
        ('IIT Palakkad', 'Electrical Engineering', 2),
        ('IIT Dharwad', 'Computer Science & Engg', 3),
        ('IIT Dharwad', 'Electrical Engineering', 2),
        ('IIT Bhilai', 'Computer Science & Engg', 3),
        ('IIT Bhilai', 'Electrical Engineering', 2),
        ('IIT Goa', 'Computer Science & Engg', 3),
        ('IIT Goa', 'Mathematics & Computing', 2),
        ('IIT Jammu', 'Computer Science & Engg', 3),
        ('IIT Jammu', 'Electrical Engineering', 2),
    ]

    branches = []
    for college, branch, seats in branches_data:
        b = Branch.objects.create(college=college, branch=branch, seats=seats)
        branches.append(b)

    student_names = [
        ('Rajit', 'Gupta'), ('Saksham', 'Jindal'), ('Majid', 'Husain'),
        ('Parth', 'Mandar'), ('Ujjwal', 'Kesari'), ('Akshat', 'Chaurasia'),
        ('Arnav', 'Singh'), ('Devesh', 'Pankaj'), ('Kanishka', 'Chakraborty'),
        ('Piusa', 'Das'), ('Vipul', 'Garg'), ('Harsh', 'Jha'),
        ('Shreya', 'Agarwal'), ('Aditya', 'Trivedi'), ('Rishabh', 'Gupta'),
        ('Devdutta', 'Majhi'), ('Shivam', 'Goyal'), ('Ananya', 'Krishnan'),
        ('Rahul', 'Khanna'), ('Om', 'Behera'), ('Sourav', 'Mishra'),
        ('Daksh', 'Rawat'), ('Vishad', 'Jain'), ('Arjun', 'Pillai'),
        ('Priya', 'Nair'), ('Rohan', 'Bansal'), ('Karthik', 'Iyer'),
        ('Sneha', 'Patil'), ('Vivek', 'Sharma'), ('Manav', 'Choudhary'),
        ('Ishaan', 'Malhotra'), ('Tanya', 'Gupta'), ('Abhishek', 'Verma'),
        ('Nikhil', 'Reddy'), ('Pooja', 'Yadav'), ('Siddharth', 'Singh'),
        ('Aarav', 'Patel'), ('Divya', 'Menon'), ('Harshit', 'Agrawal'),
        ('Lakshmi', 'Narayan'), ('Vaibhav', 'Srivastava'), ('Nandini', 'Kapoor'),
        ('Aman', 'Kumar'), ('Tushar', 'Bhatt'), ('Ritika', 'Joshi'),
        ('Mohit', 'Saxena'), ('Ankit', 'Sharma'), ('Sakshi', 'Singh'),
        ('Gaurav', 'Tiwari'), ('Meera', 'Subramaniam'), ('Pulkit', 'Garg'),
        ('Aditi', 'Bhatt'), ('Sundar', 'Rajan'), ('Kritika', 'Arora'),
        ('Dhruv', 'Pandey'), ('Isha', 'Agarwal'), ('Rajesh', 'Nair'),
        ('Pallavi', 'Reddy'), ('Shubham', 'Jha'), ('Ankita', 'Sharma'),
        ('Kunal', 'Mehta'), ('Deepika', 'Krishnan'), ('Aditya', 'Rao'),
        ('Swati', 'Gupta'), ('Pranav', 'Mishra'), ('Ruhi', 'Chauhan'),
        ('Vikram', 'Thakur'), ('Kavya', 'Menon'), ('Akash', 'Kumar'),
        ('Riya', 'Jain'), ('Sumit', 'Verma'), ('Preethi', 'Venkatesh'),
        ('Ayan', 'Bose'), ('Neha', 'Pandey'), ('Tanmay', 'Ghosh'),
        ('Sanya', 'Kapoor'), ('Himanshu', 'Chaudhary'), ('Lavanya', 'Iyer'),
        ('Arpit', 'Singh'), ('Diya', 'Nair'), ('Saurabh', 'Gupta'),
        ('Swara', 'Joshi'), ('Mayank', 'Agarwal'), ('Puja', 'Das'),
        ('Nitin', 'Tiwari'), ('Shruti', 'Sharma'), ('Venkat', 'Subramanian'),
        ('Aishwarya', 'Pillai'), ('Rohit', 'Khanna'), ('Simran', 'Kaur'),
        ('Piyush', 'Bansal'), ('Anjali', 'Rao'), ('Tarun', 'Mehta'),
        ('Bhavna', 'Singh'), ('Kushal', 'Jain'), ('Nandita', 'Bose'),
        ('Deepak', 'Sharma'), ('Sonali', 'Trivedi'), ('Akhil', 'Gupta'),
        ('Pooja', 'Nair'), ('Varun', 'Srivastava'), ('Swathi', 'Reddy'),
        ('Chirag', 'Patel'), ('Komal', 'Sharma'), ('Ritesh', 'Yadav'),
        ('Preeti', 'Arora'), ('Sahil', 'Malhotra'), ('Divyani', 'Jha'),
        ('Kartik', 'Verma'), ('Padmavathi', 'Krishnan'), ('Anmol', 'Singh'),
        ('Rupal', 'Saxena'), ('Dheeraj', 'Pandey'), ('Vinitha', 'Iyer'),
        ('Parth', 'Agarwal'), ('Chanchal', 'Gupta'), ('Niraj', 'Tiwari'),
        ('Keerthi', 'Venkataraman'), ('Shashank', 'Bhatt'), ('Madhuri', 'Nair'),
        ('Prateek', 'Joshi'), ('Swapna', 'Pillai'), ('Yash', 'Chauhan'),
        ('Sreeja', 'Menon'), ('Abhinav', 'Thakur'), ('Amrutha', 'Krishnan'),
        ('Nishant', 'Kumar'), ('Gayatri', 'Rao'), ('Soumya', 'Ghosh'),
        ('Kavitha', 'Subramaniam'), ('Vishal', 'Mishra'), ('Ramya', 'Iyer'),
        ('Kiran', 'Bajaj'), ('Sudha', 'Nair'), ('Pankaj', 'Agarwal'),
        ('Veena', 'Gupta'), ('Raghav', 'Saxena'), ('Lakshmi', 'Devi'),
        ('Dhruv', 'Malhotra'), ('Shilpa', 'Verma'), ('Ashish', 'Yadav'),
        ('Meenakshi', 'Pillai'), ('Jatin', 'Sharma'), ('Aparna', 'Bose'),
        ('Sankalp', 'Jain'), ('Indira', 'Singh'), ('Bhavik', 'Patel'),
        ('Namitha', 'Nair'), ('Shivraj', 'Singh'), ('Renuka', 'Krishnan'),
        ('Ronak', 'Mehta'), ('Lavanya', 'Subramaniam'), ('Harish', 'Chandra'),
        ('Priyanka', 'Yadav'), ('Sameer', 'Khanna'), ('Anjana', 'Pillai'),
        ('Devraj', 'Jha'), ('Shakuntala', 'Iyer'), ('Farhan', 'Shaikh'),
        ('Nithya', 'Reddy'), ('Alok', 'Mishra'), ('Sindhu', 'Nair'),
        ('Rajeev', 'Tiwari'), ('Archana', 'Gupta'), ('Mohd', 'Imran'),
        ('Shalini', 'Verma'), ('Gyanesh', 'Kumar'), ('Vasudha', 'Sharma'),
        ('Satish', 'Agarwal'), ('Nithyashri', 'Menon'), ('Rajendra', 'Prasad'),
        ('Mythri', 'Krishnan'), ('Suresh', 'Babu'), ('Pavithra', 'Rajan'),
        ('Manish', 'Jaiswal'), ('Sowmya', 'Narayanan'), ('Deepak', 'Nair'),
        ('Ranjani', 'Suresh'), ('Vikas', 'Choudhary'), ('Malathi', 'Pillai'),
        ('Suman', 'Pandey'), ('Durga', 'Prasad'), ('Girish', 'Rao'),
        ('Rekha', 'Sharma'), ('Navin', 'Kumar'), ('Usha', 'Iyer'),
        ('Pratap', 'Singh'), ('Savitha', 'Reddy'), ('Ravi', 'Shankar'),
        ('Chitra', 'Menon'), ('Sunil', 'Mehta'), ('Bhagyalakshmi', 'Devi'),
        ('Ajay', 'Krishnan'), ('Padma', 'Subramaniam'), ('Ramesh', 'Gupta'),
        ('Geetha', 'Nair'), ('Vikram', 'Reddy'), ('Saranya', 'Pillai'),
        ('Mohan', 'Lal'), ('Vasantha', 'Kumari'),
    ]

    # Preference patterns by AIR band (mirrors JoSAA cutoffs)
    # b_idx maps to branches list index (0-based)
    all_ids = list(range(len(branches)))

    def bp(top_indices, seed=0):
        rest = [i for i in all_ids if i not in top_indices]
        if seed:
            rest.sort(key=lambda x: (x * (seed + 1)) % 17)
        return top_indices + rest

    pref_patterns = {
        'top20_v0':  bp([0,5,10,14,1,6,7,11,12,15,2,16,18,22,3]),
        'top20_v1':  bp([5,0,10,14,6,1,7,12,15,11,3,16,18,22,19]),
        'top20_v2':  bp([10,5,14,0,11,12,6,7,15,1,16,18,22,3,13]),
        'top20_v3':  bp([14,10,5,0,15,16,12,6,7,11,18,1,22,3,19]),
        'top20_v4':  bp([0,5,10,14,18,1,6,12,15,7,11,16,22,2,3]),
        'air66_v0':  bp([0,5,10,14,1,6,7,12,15,11,16,18,22,2,3], 1),
        'air66_v1':  bp([5,0,14,10,6,1,12,7,15,16,11,18,22,3,19], 2),
        'air66_v2':  bp([10,5,0,14,11,12,7,6,15,1,16,18,22,19,20], 3),
        'air66_v3':  bp([14,10,5,0,15,12,16,6,7,11,1,18,22,19,26], 4),
        'air66_v4':  bp([5,10,14,0,6,7,11,1,12,15,16,18,22,26,19], 5),
        'air125_v0': bp([5,10,14,0,1,6,7,12,15,11,16,18,22,26,19], 6),
        'air125_v1': bp([10,5,14,18,6,12,7,11,1,15,16,22,26,19,29], 7),
        'air125_v2': bp([14,10,5,18,15,12,16,6,7,11,22,1,26,19,29], 8),
        'air125_v3': bp([5,14,10,18,6,7,12,1,15,11,16,22,26,29,19], 9),
        'air205_v0': bp([10,14,18,5,11,12,15,6,7,16,22,26,29,19,32], 10),
        'air205_v1': bp([14,10,18,22,15,16,12,11,6,7,26,29,19,32,35], 11),
        'air205_v2': bp([18,14,10,22,19,20,15,12,16,11,26,29,32,35,23], 12),
        'air205_v3': bp([10,18,14,22,12,11,15,19,16,6,26,29,32,23,35], 13),
        'air450_v0': bp([18,22,26,29,32,35,37,39,14,10,19,23,30,41,43], 14),
        'air450_v1': bp([22,26,29,18,23,32,35,30,37,19,39,41,43,45,47], 15),
        'air450_v2': bp([26,29,30,32,35,22,23,37,39,18,41,43,45,47,49], 16),
        'air450_v3': bp([29,30,32,35,26,37,39,41,43,45,47,49,51,53,55], 17),
        'air450_v4': bp([32,35,37,39,41,43,45,47,49,51,53,55,57,59,60], 18),
    }

    profiles = []
    prefs_to_create = []

    for i, (first, last) in enumerate(student_names):
        air = i + 1
        username = f"air{air:03d}_{first.lower()}"
        # Make username unique if collision
        if User.objects.filter(username=username).exists():
            username = f"{username}_{air}"
        user = User.objects.create_user(
            username=username,
            password='jee2025',
            first_name=first,
            last_name=last,
        )
        profile = StudentProfile.objects.create(user=user, air_rank=air, has_submitted=True)
        profiles.append(profile)

        # Pick preference pattern
        v = air % 5
        if air <= 20:
            key = f'top20_v{v}'
        elif air <= 66:
            key = f'air66_v{v}'
        elif air <= 125:
            key = f'air125_v{v % 4}'
        elif air <= 205:
            key = f'air205_v{v % 4}'
        else:
            key = f'air450_v{v}'

        ordered_indices = pref_patterns.get(key, all_ids)
        for rank, branch_idx in enumerate(ordered_indices, start=1):
            if branch_idx < len(branches):
                prefs_to_create.append(
                    Preference(student=profile, branch=branches[branch_idx], rank=rank)
                )

    Preference.objects.bulk_create(prefs_to_create, ignore_conflicts=True)
