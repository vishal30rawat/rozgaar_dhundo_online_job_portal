from django.utils import timezone
from django.core.management.utils import get_random_string


def get_extension(filename):
    return f".{filename.split('.')[-1]}"


def get_random_name(filename):
    return f'{get_random_string(6)}-{int(timezone.now().timestamp() * 1000)}{get_extension(filename)}'


def applicant_resume(instance, filename):
    new_filename = f'resume/{instance.id.hex}/{get_random_name(filename)}'
    return new_filename


def applicant_profile_picture(instance, filename):
    new_filename = f'applicant/{instance.id.hex}/{get_random_name(filename)}'
    return new_filename


def company_logo(instance, filename):
    new_filename = f'logo/{instance.id.hex}/{get_random_name(filename)}'
    return new_filename
