// static/app.js

document.addEventListener('DOMContentLoaded', function() {
    
    // --- Dynamic Student Adding ---
    const addStudentForm = document.getElementById('add-student-form');
    if (addStudentForm) {
        addStudentForm.addEventListener('submit', function(event) {
            event.preventDefault(); // Stop the default form submission

            const formData = new FormData(this);
            const name = formData.get('name').trim();
            const studentList = document.getElementById('student-list');
            const noStudentsMessage = document.getElementById('no-students-message');

            if (!name) {
                alert('Student name cannot be empty.');
                return;
            }

            fetch('/add_student', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Create the new student list item dynamically
                    const newStudent = document.createElement('li');
                    newStudent.className = 'list-item';
                    newStudent.setAttribute('data-student-id', data.id);
                    newStudent.innerHTML = `
                        <span>${data.name}</span>
                        <span class="actions">
                            <a href="/edit_student/${data.id}" class="btn-edit">Edit</a>
                            <a href="${data.view_url}" class="btn-secondary">View Grades</a>
                            <a href="${data.add_grade_url}" class="btn">Add Grade</a>
                            <form method="POST" action="/delete_student/${data.id}" class="delete-form">
                                <button type="submit" class="btn-danger">Delete</button>
                            </form>
                        </span>
                    `;
                    studentList.appendChild(newStudent);
                    
                    // Clear the input field
                    this.reset();

                    // Remove the 'no students' message if it exists
                    if (noStudentsMessage) {
                        noStudentsMessage.remove();
                    }
                } else {
                    alert('Error: ' + data.error);
                }
            })
            .catch(error => console.error('Error:', error));
        });
    }

    // --- Deletion Confirmation ---
    // Use event delegation to handle clicks on forms that may be added dynamically
    document.body.addEventListener('submit', function(event) {
        if (event.target.matches('.delete-form')) {
            const confirmed = confirm('Are you sure you want to delete this? This action cannot be undone.');
            if (!confirmed) {
                event.preventDefault(); // Stop the form submission if user cancels
            }
        }
    });

});