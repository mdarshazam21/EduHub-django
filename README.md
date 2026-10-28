# EduHub — E-Learning Platform

A Django-based e-learning platform designed to help students discover courses, enroll in learning programs, track their progress, and complete quizzes. The platform also provides tools for instructors to manage educational content.

## Features

* **User Management:** Separate areas and access permissions for students, instructors, and administrators.
* **Course Management:** Organize courses and their learning content.
* **Course Enrollment:** Allow students to enroll in available courses.
* **Quizzes:** Support assessments and knowledge checks.
* **Progress Tracking:** Track student learning progress.
* **Certificates:** Organize course completion certificates.
* **Search and Filtering:** Help users find relevant courses.
* **Django Admin:** Manage application data through Django's administration interface.

## Tech Stack

* **Language:** Python
* **Backend Framework:** Django
* **Database:** SQLite for local development
* **Frontend:** HTML, CSS, Django Templates
* **Version Control:** Git and GitHub

## Project Structure

```text
elearning_platform/
├── accounts/             # User accounts and roles
├── certificates/         # Certificate functionality
├── courses/              # Course management and enrollment
├── elearning_project/    # Django project configuration
├── progress/             # Student progress tracking
├── quizzes/              # Quiz functionality
├── static/               # Static assets
├── templates/            # HTML templates
├── .gitignore            # Files excluded from Git
├── manage.py             # Django management utility
└── README.md             # Project documentation
```

## Getting Started

### Prerequisites

* Python 3.10 or a compatible version supported by your dependencies
* pip
* Git

### 1. Clone the repository

```bash
git clone https://github.com/mdarshazam21/EduHub-django.git
cd EduHub-django
```

### 2. Create a virtual environment

**Windows PowerShell:**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

Install the packages required by your project:

```powershell
pip install django python-dotenv
```

If you maintain a `requirements.txt` file, use that instead:

```powershell
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root and set your Django secret key:

```env
DJANGO_SECRET_KEY=replace_with_your_own_secret_key
```

Use your own secret key. Never publish the `.env` file or commit production secrets to GitHub.

### 5. Apply database migrations

```powershell
python manage.py migrate
```

### 6. Create an administrator account

```powershell
python manage.py createsuperuser
```

Follow the prompts to create your account.

### 7. Start the development server

```powershell
python manage.py runserver
```

Open the local development address shown in your terminal to access the application.

## Environment and Security

* Keep `.env` and its secrets out of version control.
* Do not commit your local database or virtual environment.
* Configure production settings and environment variables before deployment.
* Use a production-ready database and web server when deploying the application.

## Future Improvements

Potential improvements include payment gateway integration, automated tests, deployment automation, and enhanced instructor analytics.

## Author

**MD Arsh Azam**

GitHub: [mdarshazam21](https://github.com/mdarshazam21)
