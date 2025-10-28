document.addEventListener('DOMContentLoaded', () => {
    const MinPassLength = 8;

    // Login Form
    const loginForm = document.getElementById('form');
    if (loginForm) {
        loginForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const email = document.getElementById('email').value;
            const password = document.getElementById('pass').value;
            const rememberMe = document.querySelector('input[value="remember"]').checked;
            const users = JSON.parse(localStorage.getItem('users')) || [];
            const user = users.find(u => u.email === email);

            if (!user) {
                alert("Username or email not registered.");
                return;
            }

            if (user.password !== password) {
                alert("Incorrect password.");
                return;
            }

            if (rememberMe) {
                localStorage.setItem('rememberMe', JSON.stringify({ email, password }));
            } else {
                localStorage.removeItem('rememberMe');
            }

            alert("Login successful!");
            window.location.href = "/Index.html";
        });

        // Toggle 
        const togglePasswordButton = document.getElementById('togglePassword');
        const passwordField = document.getElementById('pass');
        togglePasswordButton.addEventListener('click', () => {
            const type = passwordField.getAttribute('type') === 'password' ? 'text' : 'password';
            passwordField.setAttribute('type', type);
            togglePasswordButton.querySelector('i').classList.toggle('fa-eye-slash');
        });

        const rememberedUser = JSON.parse(localStorage.getItem('rememberMe'));
        if (rememberedUser) {
            document.getElementById('email').value = rememberedUser.email;
            document.getElementById('pass').value = rememberedUser.password;
            document.querySelector('input[value="remember"]').checked = true;
        }
    }

    // Registration Form
    const registrationForm = document.getElementById('registrationForm');
    if (registrationForm) {
        registrationForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const firstName = document.getElementById('firstName').value;
            const lastName = document.getElementById('lastName').value;
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            const confirmPassword = document.getElementById('confirmPass').value;
            const agreeTerms = document.querySelector('input[value="agree"]').checked;

            if (password.length < MinPassLength) {
                alert(`Password must be at least ${MinPassLength} characters long.`);
                return;
            }

            if (password !== confirmPassword) {
                alert("Passwords do not match.");
                return;
            }

            const emailTaken = await checkEmailAvailability(email);
            if (emailTaken) {
                alert("Email taken. Please choose another one.");
                return;
            }

            let users = JSON.parse(localStorage.getItem('users')) || [];
            users.push({ firstName, lastName, email, password });
            localStorage.setItem('users', JSON.stringify(users));
            alert("Registration successful!");
            window.location.href = "Login_Successfully.html";
        });

        async function checkEmailAvailability(email) {
            const users = JSON.parse(localStorage.getItem('users')) || [];
            return users.some(user => user.email === email);
        }

        // Toggle 
        const togglePasswordButtonRegister = document.getElementById('togglePassword');
        const passwordFieldRegister = document.getElementById('password');
        togglePasswordButtonRegister.addEventListener('click', () => {
            const type = passwordFieldRegister.getAttribute('type') === 'password' ? 'text' : 'password';
            passwordFieldRegister.setAttribute('type', type);
            togglePasswordButtonRegister.querySelector('i').classList.toggle('fa-eye-slash');
        });

        const toggleConfirmPasswordButton = document.getElementById('toggleConfirmPassword');
        const confirmPasswordField = document.getElementById('confirmPass');
        toggleConfirmPasswordButton.addEventListener('click', () => {
            const type = confirmPasswordField.getAttribute('type') === 'password' ? 'text' : 'password';
            confirmPasswordField.setAttribute('type', type);
            toggleConfirmPasswordButton.querySelector('i').classList.toggle('fa-eye-slash');
        });
    }
});

var modal = document.getElementById("myModalfooter2");
var btn = document.getElementById("myBtn");
var span = document.getElementsByClassName("close")[0];

btn.onclick = function() {
    modal.style.display = "block";
}

span.onclick = function() {
    modal.style.display = "none";
}

window.onclick = function(event) {
    if (event.target == modal) {
        modal.style.display = "none";
    }
}

var togglePassword = document.getElementById("togglePassword");
var password = document.getElementById("password");

togglePassword.addEventListener("click", function() {
    const type = password.getAttribute("type") === "password" ? "text" : "password";
    password.setAttribute("type", type);
    this.querySelector("i").classList.toggle("fa-eye");
    this.querySelector("i").classList.toggle("fa-eye-slash");
});

var toggleConfirmPassword = document.getElementById("toggleConfirmPassword");
var confirmPassword = document.getElementById("confirmPass");

toggleConfirmPassword.addEventListener("click", function() {
    const type = confirmPassword.getAttribute("type") === "password" ? "text" : "password";
    confirmPassword.setAttribute("type", type);
    this.querySelector("i").classList.toggle("fa-eye");
    this.querySelector("i").classList.toggle("fa-eye-slash");
});

