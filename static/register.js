document.addEventListener("DOMContentLoaded", () => {
    const registerForm = document.getElementById("registerForm");
  
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
  
          const signupRes = await fetch(`/api/register`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, email, password })
          });
  
          if (signupRes.ok) {
            alert("회원가입 완료! 로그인 페이지로 이동합니다.");
            window.location.href = "/login";
          } else {
            alert("회원가입에 실패했습니다. 다시 시도해주세요.");
          }
  
        } catch (err) {
          console.error(err);
          alert("서버 오류가 발생했습니다.");
        }
      });
    }
  });
  document.getElementById('reg-username').addEventListener('blur', () => {
    const username = document.getElementById('reg-username').value;
    fetch('/api/check-duplicate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username })
    })
    .then(res => res.json())
    .then(data => {
      if (data.usernameExists) {
        alert('이미 사용 중인 아이디입니다.');
      }
    });
  });
  
  document.getElementById('reg-email').addEventListener('blur', () => {
    const email = document.getElementById('reg-email').value;
    fetch('/api/check-duplicate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email })
    })
    .then(res => res.json())
    .then(data => {
      if (data.emailExists) {
        alert('이미 등록된 이메일입니다.');
      }
    });
  });
  