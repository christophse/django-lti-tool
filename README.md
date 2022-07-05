# django-lti-tool

Django-lti-tool transforms your Django installation into a LTI 1.3 tool provider.

It is tightly integrated into Django and maps LTI entities (platforms, contexts, resources, users) into Django's ORM. This decouples the platform (e.g. Moodle) and the tool. Students are able to work on their assignments independently from the platform. Grades can be transferred to the platform afterwards.

## Features
|Specification|Status|
|-|-|
|LTI 1.3 (Core)|Yes|
|Assignment and Grade Service|Yes|
|Deep Linking|WIP|
|Names and Role Provisioning Services|No|

## Quick Setup

After setting up Django, install django-lti-tool using `pip`:
```shell
pip install git+https://github.com/christophse/django-lti-tool.git
```
Prepare your `settings.py`:
1. Add `lti_tool` to `INSTALLED_APPS`.
2. Add `lti_tool.middleware.LTIMiddleware` to `MIDDLEWARE` prior to
   `CsrfViewMiddleware`.
3. Add `lti_tool.auth.LTIBackend` to `AUTHENTICATION_BACKENDS`.

Initialize the ORM:
```shell
python manage.py makemigrations lti_tool && python manage.py migrate
```
## Credits

Django-lti-tool is developed at [Open Distributed Systems Chair](https://www.ods.tu-berlin.de/).
