from enum import Enum


class ChoiceEnum(Enum):
    @classmethod
    def get_value(cls, member):
        return cls[member].value[0]

    @classmethod
    def get_choices(cls):
        return tuple(x.value for x in cls)


class PayRollChoice(ChoiceEnum):
    hourly = ('H', 'Hourly')
    weekly = ('W', 'Weekly')
    monthly = ('M', 'Monthly')
    annually = ('A', 'Annually')


class JobApplicationStatus(ChoiceEnum):
    candidate_applied = ('APP', 'Candidate Applied')
    company_declined = ('DEC', 'Company Declined')
    company_accepted = ('ACC', 'Company Accepted')
