import unittest
from collections import Counter

from ratio_sampler import ActivityFamilyBatchSampler, FALL_ACTIVITIES, balanced_activity_counts


def fixture():
    labels=[]; sources=[]; activities=[]; families=[]
    for index in range(100): labels.append(0); sources.append("real_adl"); activities.append("A01"); families.append("")
    for activity in FALL_ACTIVITIES:
        for index in range(10): labels.append(1); sources.append("real_fall"); activities.append(activity); families.append("")
        for family in range(8):
            for variant in range(1+(family%3)): labels.append(1); sources.append("synthetic_fall"); activities.append(activity); families.append(f"{activity}_F{family}")
    return labels,sources,activities,families


class SamplerTests(unittest.TestCase):
    def test_activity_counts(self):
        self.assertEqual(sum(balanced_activity_counts(18).values()),18)
        self.assertLessEqual(max(balanced_activity_counts(18).values())-min(balanced_activity_counts(18).values()),1)

    def test_exact_60_40(self):
        labels,sources,activities,families=fixture(); sampler=ActivityFamilyBatchSampler(labels,sources,activities,families,60,1,11,18,12); batch=next(iter(sampler)); counts=Counter(sources[index] for index in batch)
        self.assertEqual(counts,{"real_adl":30,"real_fall":18,"synthetic_fall":12})

    def test_exact_40_60(self):
        labels,sources,activities,families=fixture(); sampler=ActivityFamilyBatchSampler(labels,sources,activities,families,60,1,11,12,18); batch=next(iter(sampler)); counts=Counter(sources[index] for index in batch)
        self.assertEqual(counts,{"real_adl":30,"real_fall":12,"synthetic_fall":18})

    def test_real_only(self):
        labels,sources,activities,families=fixture(); sampler=ActivityFamilyBatchSampler(labels,sources,activities,families,60,1,11,30,0); batch=next(iter(sampler)); self.assertEqual(Counter(sources[index] for index in batch),{"real_adl":30,"real_fall":30})

    def test_synthetic_family_first_no_repeat_when_pool_sufficient(self):
        labels,sources,activities,families=fixture(); sampler=ActivityFamilyBatchSampler(labels,sources,activities,families,60,1,11,18,12); batch=next(iter(sampler))
        for activity in FALL_ACTIVITIES:
            chosen=[families[index] for index in batch if sources[index]=="synthetic_fall" and activities[index]==activity]
            self.assertEqual(len(chosen),len(set(chosen)))


if __name__=="__main__": unittest.main()
