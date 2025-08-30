document.addEventListener('DOMContentLoaded', () => {
    // Add confirmation dialogs to all delete forms
    const deleteForms = document.querySelectorAll('.delete-form');
    deleteForms.forEach(form => {
        form.addEventListener('submit', (event) => {
            const confirmed = confirm('Are you sure you want to delete this? This action cannot be undone.');
            if (!confirmed) {
                event.preventDefault(); // Stop the form submission if the user clicks "Cancel"
            }
        });
    });
});