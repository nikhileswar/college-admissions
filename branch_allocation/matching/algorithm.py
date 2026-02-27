"""
Gale-Shapley Stable Matching (Student-Proposing / Student-Optimal)

Students propose to branches in order of their preference.
Branches accept the best student (by AIR rank, lower = better)
they can hold, displacing a weaker student if over capacity.

The result is stable: no student and branch can both prefer
each other over their current assignment.
"""
from .models import (
    Branch, StudentProfile, Preference,
    MatchingResult, Allotment
)


def run_gale_shapley():
    """
    Run the student-proposing Gale-Shapley algorithm.
    Returns the MatchingResult instance.
    """
    students = list(StudentProfile.objects.all().select_related('user'))
    branches = list(Branch.objects.all())

    if not students or not branches:
        return None

    # Build preference list per student: {student_id: [branch_id, ...]}
    prefs = {}
    for s in students:
        ordered = (
            Preference.objects
            .filter(student=s)
            .order_by('rank')
            .values_list('branch_id', flat=True)
        )
        if ordered:
            prefs[s.id] = list(ordered)
        else:
            # No preferences submitted → default to all branches ordered by id
            prefs[s.id] = [b.id for b in branches]

    # College preference over students: lower AIR rank = better
    # air_rank=None → treated as worst
    def air(sid):
        s = next((x for x in students if x.id == sid), None)
        return s.air_rank if (s and s.air_rank) else 999999

    # Proposal index per student
    prop_idx = {s.id: 0 for s in students}

    # Current holders per branch slot: {branch_id: [student_id, ...]}
    slots = {b.id: [] for b in branches}
    branch_map = {b.id: b for b in branches}

    free = [s.id for s in students]

    max_iter = len(students) * len(branches) + 10
    it = 0

    while free and it < max_iter:
        it += 1
        sid = free.pop(0)
        pref_list = prefs.get(sid, [])
        idx = prop_idx[sid]

        if idx >= len(pref_list):
            continue  # exhausted all preferences

        bid = pref_list[idx]
        prop_idx[sid] += 1

        branch = branch_map.get(bid)
        if not branch:
            free.append(sid)
            continue

        holders = slots[bid]

        if len(holders) < branch.seats:
            holders.append(sid)
        else:
            # Find worst holder by AIR rank (higher rank number = worse)
            worst = max(holders, key=lambda h: air(h))
            if air(sid) < air(worst):
                holders.remove(worst)
                holders.append(sid)
                free.append(worst)
            else:
                free.append(sid)

    # Deactivate old results
    MatchingResult.objects.filter(is_active=True).update(is_active=False)

    # Count stats
    matched_ids = set(sid for holders in slots.values() for sid in holders)
    unmatched = [s for s in students if s.id not in matched_ids]
    total_seats = sum(b.seats for b in branches)

    result = MatchingResult.objects.create(
        is_active=True,
        total_matched=len(matched_ids),
        total_unmatched=len(unmatched),
        total_unfilled=total_seats - len(matched_ids),
    )

    # Build allotments
    allotments = []

    for bid, holders in slots.items():
        for sid in holders:
            pref_list = prefs.get(sid, [])
            pref_rank = pref_list.index(bid) + 1 if bid in pref_list else None
            allotments.append(Allotment(
                result=result,
                student_id=sid,
                branch_id=bid,
                preference_rank=pref_rank,
                is_matched=True,
            ))

    for s in unmatched:
        allotments.append(Allotment(
            result=result,
            student=s,
            branch=None,
            preference_rank=None,
            is_matched=False,
        ))

    Allotment.objects.bulk_create(allotments)
    return result
