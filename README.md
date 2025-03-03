# **Ft_Transcendence**

## **Overview**
Ft_Transcendence is a **full-stack web application** designed to provide a seamless and interactive user experience. The project combines **frontend and backend technologies** to deliver a scalable and responsive application. It includes features like user authentication, real-time interactions, and a robust database system.

## **Features**
- **User Authentication**: Secure login and registration system.
- **Real-Time Interactions**: Real-time chat and notifications.
- **Responsive Design**: Optimized for both desktop and mobile devices.
- **Scalable Architecture**: Built with containerization for easy deployment and scaling.
- **Database Management**: Efficient data storage and retrieval using PostgreSQL.

## **Technologies Used**
- **Frontend**: React, Tailwind CSS
- **Backend**: Django, Django REST Framework
- **Database**: PostgreSQL
- **Containerization**: Docker
- **Other Tools**: NGINX (for reverse proxying), Git (for version control)

## **Installation**
Follow these steps to set up and run the project locally:

### **Prerequisites**
- Docker and Docker Compose installed on your machine.
- Git for cloning the repository.

### **Steps**
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/HKEV07/TranDaDan.git
   cd TranDaDan
   ```

2. **Environment Setup**:
   - Create a `.env` file in the root directory based on the provided `.env.example`
   ```bash
   cp .env.template .env
   # Edit the .env file with your specific configuration values
   ```

3. **Build and Start the Containers**:
   ```bash
   make build  # Build the Docker containers
   make up     # Start the application
   ```

4. **Access the Application**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000/api
   - Database Admin: http://localhost:8000/admin (username: admin, password: see .env file)

## **Makefile Commands**
The project includes a Makefile with the following commands:

- `make up` - Build and start the containers in detached mode
- `make down` - Stop and remove the containers
- `make logs` - View the container logs
- `make build` - Build the Docker containers
- `make stop` - Stop the containers without removing them
- `make clean` - Remove all Docker resources (containers, volumes, networks)

## **Project Structure**
```
TranDaDan/
├── backend/                   # Django application
│   ├── api/                   # API endpoints
│   ├── config/                # Django settings
│   ├── manage.py              # Django management script
│   └── requirements.txt       # Python dependencies
├── nginx/                     # NGINX configuration
|   ├── frontend/                  # React application
|   │   ├── public/                # Static files
|   │   ├── src/                   # Source code
|   │   └── package.json           # Dependencies
├── docker-compose.yml         # Docker setup
├── Makefile                   # Project management commands
├── .env.template              # Environment variables template
└── README.md                  # Project documentation
```

## **Development**
All development is done through Docker containers using the provided Makefile.

### **Database Migrations**
When making changes to the database models:
```bash
docker-compose exec backend python manage.py makemigrations
docker-compose exec backend python manage.py migrate
```

## **Testing**
Run the test suites with the following commands:

### **Frontend Tests**
```bash
docker-compose exec frontend npm test
```

### **Backend Tests**
```bash
docker-compose exec backend python manage.py test
```

## **Deployment**
The application is designed to be deployed using Docker:

1. **Update Environment Variables**:
   - Ensure all production environment variables are set correctly in your deployment environment

2. **Build and Deploy**:
   ```bash
   make build
   make up
   ```

3. **To Stop the Application**:
   ```bash
   make down
   ```

4. **To View Logs**:
   ```bash
   make logs
   ```

## **Acknowledgments**
- Special thanks to all contributors who have participated in this project.
- Inspired by various web technologies and best practices.

## **Contact**
For any questions or suggestions, please open an issue in the repository or contact the repository owner.

