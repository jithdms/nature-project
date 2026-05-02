document.addEventListener("DOMContentLoaded", () => {
  const registerForm = document.getElementById("registerForm");
  const loginForm = document.getElementById("loginForm");

  // 회원가입 처리
  if (registerForm) {
    registerForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const username = document.getElementById("reg-username").value.trim();
      const email = document.getElementById("reg-email").value.trim();
      const password = document.getElementById("reg-password").value;
      const confirm = document.getElementById("reg-confirm").value;

      if (password !== confirm) {
        alert("비밀번호가 일치하지 않습니다.");
        return;
      }

      // ✅ 아이디/이메일 중복 확인 (백엔드 연동 필요, 임시 예시)
      try {
        const res = await fetch(`/api/check-duplicate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username, email })
        });
        const data = await res.json();

        if (data.usernameExists) {
          alert("이미 사용 중인 아이디입니다.");
          return;
        }

        if (data.emailExists) {
          alert("이미 사용 중인 이메일입니다.");
          return;
        }

        // ✅ 회원가입 요청 (예시, 실제 API 연동 필요)
        const signupRes = await fetch(`/api/register`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username, email, password })
        });

        if (signupRes.ok) {
          alert("회원가입 완료! 로그인 페이지로 이동합니다.");
          window.location.href = "login.html";
        } else {
          alert("회원가입에 실패했습니다. 다시 시도해주세요.");
        }

      } catch (err) {
        console.error(err);
        alert("서버 오류가 발생했습니다.");
      }
    });
  }

  // 로그인 처리
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
