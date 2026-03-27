/**
 * EduTrack - Unified Frontend Logic
 * Handles Role Switching, Animations, and Modal Systems
 */

// --- Role Switching & Animations (Login/Register) ---

function triggerAnimation(ids) {
    ids.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.classList.remove('animate-switch');
            void el.offsetWidth; // Force a DOM reflow to restart css animation
            el.classList.add('animate-switch');
        }
    });
}

function setRole(role) {
    // Detect which page we are on based on existing elements
    const pageType = document.getElementById('lbl-name') ? 'register' : 'login';

    // Update Toggle Button states
    const btnStudent = document.getElementById('btn-student');
    const btnTeacher = document.getElementById('btn-teacher');
    if (btnStudent) btnStudent.classList.remove('active');
    if (btnTeacher) btnTeacher.classList.remove('active');

    const activeBtn = document.getElementById('btn-' + role);
    if (activeBtn) activeBtn.classList.add('active');

    // Move Physical slider container
    const toggleContainer = document.getElementById('role_toggle_container');
    if (toggleContainer) toggleContainer.setAttribute('data-active', role);

    // Update Hidden input for backend validation
    const roleInput = document.getElementById('role_type');
    if (roleInput) roleInput.value = role;

    // Element references
    const title = document.getElementById('title');
    const subtitle = document.getElementById('subtitle');
    const lblUsername = document.getElementById('lbl-username');
    const usernameInput = document.getElementById('username');
    const createLink = document.getElementById('create_account_link');
    const submitBtn = document.getElementById('btn-submit-login');

    if (pageType === 'login') {
        if (role === 'student') {
            if (title) title.innerText = 'Welcome Back, Student!';
            if (subtitle) subtitle.innerText = 'Track your grades, attendance, and progress.';
            if (lblUsername) lblUsername.innerText = 'ROLL NUMBER';
            if (usernameInput) usernameInput.placeholder = 'e.g. STU001';
            if (createLink) createLink.innerText = 'New Student? Create an Account';
        } else {
            if (title) title.innerText = 'Welcome Back, Teacher!';
            if (subtitle) subtitle.innerText = 'Manage your courses and students.';
            if (lblUsername) lblUsername.innerText = 'FACULTY ID';
            if (usernameInput) usernameInput.placeholder = 'e.g. FAC001';
            if (createLink) createLink.innerText = 'New Teacher? Apply for Access';
        }
        triggerAnimation(['title', 'subtitle', 'lbl-username', 'username', 'btn-submit-login', 'create_account_link']);
    } else {
        // Registration page logic
        const lblName = document.getElementById('lbl-name');
        const nameInput = document.getElementById('name');

        if (role === 'student') {
            if (title) title.innerText = 'Create Student Account';
            if (subtitle) subtitle.innerText = 'Join EduTrack to monitor your academic progress.';
            if (lblUsername) lblUsername.innerText = 'ROLL NUMBER';
            if (usernameInput) usernameInput.placeholder = 'e.g. STU001';
        } else {
            if (title) title.innerText = 'Create Teacher Account';
            if (subtitle) subtitle.innerText = 'Join EduTrack to manage your courses and students.';
            if (lblUsername) lblUsername.innerText = 'FACULTY ID';
            if (usernameInput) usernameInput.placeholder = 'e.g. FAC001';
        }
        triggerAnimation(['title', 'subtitle', 'lbl-name', 'name', 'lbl-username', 'username', 'btn-submit-login']);
    }
}

// --- Modal System (Student Dashboard) ---

function openProfileModal() {
    const modal = document.getElementById('profileModal');
    if (modal) {
        modal.style.display = 'block';
        setTimeout(() => modal.classList.add('show'), 10);
    }
}

function closeProfileModal() {
    const modal = document.getElementById('profileModal');
    if (modal) {
        modal.classList.remove('show');
        setTimeout(() => modal.style.display = 'none', 300);
    }
}

function openSubjectModal() {
    const modal = document.getElementById('subjectModal');
    if (modal) {
        modal.style.display = 'block';
        setTimeout(() => modal.classList.add('show'), 10);
    }
}

function closeSubjectModal() {
    const modal = document.getElementById('subjectModal');
    if (modal) {
        modal.classList.remove('show');
        setTimeout(() => modal.style.display = 'none', 300);
    }
}

// Close modals when clicking overlay
window.addEventListener('click', function (event) {
    const profileModal = document.getElementById('profileModal');
    const subjectModal = document.getElementById('subjectModal');
    if (event.target === profileModal) closeProfileModal();
    if (event.target === subjectModal) closeSubjectModal();
});
