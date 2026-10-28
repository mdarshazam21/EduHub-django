# EduHub — E-Learning Platform

EduHub is a Django-based e-learning platform designed to organize online courses and support students throughout their learning journey. The project includes separate Django applications for accounts, courses, quizzes, student progress, and certificates.

## Features

* **User Management:** Account management and role-based access for students, instructors, and administrators.
* **Course Management:** Organize and manage online courses.
* **Course Enrollment:** Support student enrollment in courses.
* **Quizzes:** Provide assessments to evaluate student understanding.
* **Progress Tracking:** Track student learning progress.
* **Certificates:** Support course completion certificates.
* **Course Discovery:** Search and filter available courses.
* **Admin Interface:** Manage application data using Django Admin.

> Note: Features listed above should match the functionality currently implemented in the project.

## Technology Stack

| Technology            | Purpose                                 |
| --------------------- | --------------------------------------- |
| Python                | Programming language                    |
| Django                | Backend web framework                   |
| Django REST Framework | REST API development                    |
| SQLite                | Local development database              |
| PostgreSQL            | Supported database connectivity         |
| HTML and CSS          | Frontend templates and styling          |
| Git and GitHub        | Version control and source code hosting |

## Project Structure

```text
elearning_platform/
├── accounts/
├── certificates/
├── courses/
├── elearning_project/
├── progress/
├── quizzes/
├── static/
├── templates/
├── .gitignore
├── manage.py
├── requirements.txt
└── README.md
```

## Installation and Setup

### Prerequisites

* Python compatible with the versions of Django and other dependencies in `requirements.txt`
* Git
* pip

### 1. Clone the repository

```bash
git clone https://github.com/mdarshazam21/EduHub-django.git
cd EduHub-django
```

### 2. Create and activate a virtual environment

**Windows PowerShell:**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root, alongside `manage.py`.

Add the following configuration:

```env
DJANGO_SECRET_KEY=replace_with_your_own_secret_key
```

Replace the placeholder with a securely generated Django secret key. Never commit your `.env` file or expose secret keys publicly.

### 5. Apply database migrations

```powershell
python manage.py migrate
```

### 6. Create a superuser

```powershell
python manage.py createsuperuser
```

Follow the prompts to create an administrator account.

### 7. Start the development server

```powershell
python manage.py runserver
```

Open the local address displayed in your terminal to access the application.

## Security Notes

* Keep secret keys and credentials in environment variables.
* Do not commit `.env`, `.venv`, or local database files.
* Use appropriate production settings before deployment.
* Configure a production-ready database and web server when deploying.

## Future Improvements

Potential improvements include expanded automated testing, payment integration, instructor analytics, and deployment automation.

## Author

**MD Arsh Azam**

GitHub: [mdarshazam21](https://github.com/mdarshazam21)

## License

No license has been specified yet.
