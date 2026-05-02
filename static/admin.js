function searchUser() {
  const userId = document.getElementById("user-search").value;
  if (!userId) {
    alert("유저 ID를 입력해주세요.");
    return;
  }

  fetch(`/admin/user/${userId}`)
    .then(res => res.json())
    .then(data => {
      const tbody = document.getElementById("user-result");

      if (data.found) {
        tbody.innerHTML = `
          <tr>
            <td>${data.id}</td>
            <td>${data.username}</td>
            <td>${data.email || '-'}</td>
            <td>${data.created_at}</td>
            <td>${data.point}P</td>
            <td>${data.grade_id ?? '-'}</td>
            <td>${data.is_admin ? '🛡 관리자' : '일반'}</td>
          </tr>
        `;
      } else {
        tbody.innerHTML = `
          <tr>
            <td colspan="7" style="color: red;">❌ 해당 유저를 찾을 수 없습니다.</td>
          </tr>
        `;
      }
    })
    .catch(err => {
      alert("유저 정보를 불러오는 중 오류가 발생했습니다.");
      console.error(err);
    });
}

function applyPoints() {
  const userId = document.getElementById("point-user-id").value;
  const amount = parseInt(document.getElementById("point-amount").value);
  if (!userId || isNaN(amount)) {
    alert("포인트 적용 정보를 잘 입력해주세요.");
    return;
  }
  alert(`검색 및 적용: ${userId} - ${amount}P`);
}

function searchUser() {
  const keyword = document.getElementById("user-search").value;

  fetch(`/admin/users?keyword=${encodeURIComponent(keyword)}`)
    .then(res => res.json())
    .then(data => {
      const tbody = document.getElementById("user-result");
      tbody.innerHTML = ""; // 기존 내용 비우기

      if (data.length === 0) {
        tbody.innerHTML = "<tr><td colspan='7'>검색 결과 없음</td></tr>";
        return;
      }

      data.forEach(user => {
        const row = document.createElement("tr");
        row.innerHTML = `
          <td>${user[0]}</td>  <!-- id -->
          <td>${user[1]}</td>  <!-- username -->
          <td>${user[2]}</td>  <!-- email -->
          <td>${user[3]}</td>  <!-- created_at -->
          <td>${user[4]}</td>  <!-- point -->
          <td>${user[5]}</td>  <!-- grade_id -->
          <td>${user[6] ? "관리자" : "일반유저"}</td>  <!-- is_admin -->
        `;
        tbody.appendChild(row);
      });
    });
}

// 페이지 로드시 전체 유저 자동 로딩
window.onload = function() {
  searchUser();
};

function applyPoints() {
  const userId = document.getElementById("point-user-id").value;
  const amount = parseInt(document.getElementById("point-amount").value);

  if (!userId || isNaN(amount)) {
    alert("유저 ID와 포인트 수를 정확히 입력하세요.");
    return;
  }

  fetch("/admin/point", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ identifier: userId, amount: amount })
  })
    .then(res => res.json())
    .then(data => {
      alert(data.message);
      searchUser();  // ✅ 포인트 적용 후 유저 테이블 다시 불러오기
    });
}
