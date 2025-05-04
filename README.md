 🚀 Job Portal

A modern, responsive **web-based job portal** built with **Flask**. Job seekers can browse and apply for open positions, while employers can post and manage listings—all in a sleek, user-friendly interface.


 ✨ Features

* 🎫 **User Authentication**: Secure signup/login for job seekers and employers.
* 📋 **Job Listings**: Create, view, filter, and search job posts.
* 📝 **Resume Upload**: Job seekers can upload resumes (PDF/DOCX).
* 🔒 **Admin Dashboard**: Approve, edit, or remove listings.
* 📧 **Email Notifications**: Alerts for new applications and postings.


 🛠 Tech Stack

* **Flask** – Lightweight Python web framework
* **SQLite** – Embedded database (via SQLAlchemy)
* **HTML5 & CSS3** – Responsive design
* **Bootstrap** – UI components & grid system
* **JavaScript** – Frontend interactivity
* **GitHub Actions** – CI/CD pipeline


 🚀 Installation

### Clone the repo

```bash
git clone https://github.com/yourusername/job-portal.git
cd job-portal
```

### Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Initialize database

```bash
flask db upgrade  # if using Flask-Migrate
# or:
python schema.sql  # create tables manually
```

### Run the application

```bash
export FLASK_APP=app.py
export FLASK_ENV=development  # for hot reload
flask run
```

Your app will run on `http://127.0.0.1:5000/`

**Docker**

```bash
# Build image
docker build -t job-portal .
# Run container
docker run -d -p 5000:5000 job-portal
```

---

## 👉 Usage

1. **Register** as a job seeker or employer.
2. **Browse** available listings or **post** new jobs.
3. **Upload** your resume and **apply** quickly.
4. **Review** application status in your dashboard.

---

## 📂 Project Structure

```text
job-portal/
├── app.py            # Flask application entry point
├── job_portal.db     # SQLite database file
├── requirements.txt  # Python dependencies
├── schema.sql        # SQL schema for database tables
├── static/           # Static assets (CSS, JS, images)
│   └── images/       # Screenshots and logos
├── templates/        # Jinja2 HTML templates
└── uploads/          # User-uploaded files (resumes)
```

---

## 🗄 Database Schema

Defined in `schema.sql`. Key tables:

* `users` (id, username, email, password\_hash, role)
* `jobs` (id, title, description, company, location, posted\_by)
* `applications` (id, job\_id, user\_id, resume\_path, status)
* `reviews` (id, job\_id, user\_id, rating, comment, created\_at)

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/YourFeature`)
3. Commit your changes (`git commit -m "Add YourFeature"`)
4. Push to branch (`git push origin feature/YourFeature`)
5. Open a Pull Request

Please adhere to the [code of conduct](CODE_OF_CONDUCT.md).

---

## 📜 License

Distributed under the **MIT License**. See `LICENSE` for details.

---

## 📬 Contact

* **Author** : moiz87siddiqui@gmail.com
* **GitHub** \https://github.com/MMoizSiddiqui/


