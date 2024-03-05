
const pswrd_1 = document.querySelector("#pass1");
const pswrd_2 = document.querySelector("#pass2");
const btn = document.querySelector("#submitBtn");
const errorText = document.querySelector(".error-text");
function active() {
   if(pswrd_1.value.length >= 3) {  // TODO: change to 8
       btn.removeAttribute("disabled");
       btn.classList.add("active");
       pswrd_2.removeAttribute("disabled");
   } else {
       btn.setAttribute("disabled", "");
       btn.classList.remove("active");
       pswrd_2.setAttribute("disabled", "");
   }
}
btn.onclick = function() {
   if(pswrd_1.value !== pswrd_2.value) {
       errorText.style.display = "block";
       errorText.classList.remove("matched");
       errorText.textContent = "Error! Passwords Did Not Match!";
       return false;
   } else {
       errorText.style.display = "block";
       errorText.classList.add("matched");
       errorText.textContent = "Registration successful! Redirecting...";
       return true;
   }
}
