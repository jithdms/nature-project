document.addEventListener("DOMContentLoaded", () => {
    const loginForm = document.getElementById("loginForm");
  
    if (loginForm) {
      loginForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const username = document.getElementById("login-username").value.trim();
        const password = document.getElementById("login-password").value;
  
        try {
          const res = await fetch(`/api/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password })
          });
  
          if (res.ok) {
            alert("로그인 성공! 홈으로 이동합니다.");
            window.location.href = "index.html";
          } else {
            alert("아이디나 비밀번호가 일치하지 않습니다.");
          }
  
        } catch (err) {
          console.error(err);
          alert("서버 오류가 발생했습니다.");
        }
      });
    }
  });
  