function toggleGradeInfo() {
  const box = document.getElementById('gradeBox');
  const info = document.getElementById('gradeInfo');
  const arrow = document.getElementById('arrow');

  box.classList.toggle('open');
  arrow.textContent = box.classList.contains('open') ? '▼' : '▶';
}

function openModal(id) {
  document.getElementById(id).style.display = "flex"; // 중앙 정렬 위해 flex 사용
}

function closeModal(id) {
  document.getElementById(id).style.display = "none";

  if (id === "modal-recycle") {
    // ✅ 분리배출 모달 닫았을 때만 새로고침
    location.reload();
  }
}


// ================= 지도 초기화 ===================
function initMaps() {
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(position => {
      const userLocation = {
        lat: position.coords.latitude,
        lng: position.coords.longitude,
      };

      const options = {
        center: userLocation,
        zoom: 15,
      };

      const transportMap = new google.maps.Map(document.getElementById("map-transport"), options);
      new google.maps.Marker({ position: userLocation, map: transportMap, title: "현재 위치" });

      const bikeMap = new google.maps.Map(document.getElementById("map-bike"), options);
      new google.maps.Marker({ position: userLocation, map: bikeMap, title: "현재 위치" });
    }, () => {
      console.warn("위치 정보를 가져올 수 없습니다.");
    });
  }
}

// ================= 걷기 ===========================
let stepCount = 0;

function updateStepCount(newStep) {
  stepCount = newStep;
  document.getElementById('step-count').textContent = `걸음 수: ${stepCount}보`;
}

// ================= 대중교통 =======================
let startCoords = null;
let startTime = null;

function startTracking() {
  const type = document.getElementById('transport-type').value;
  if (!type) {
    alert("🚨 교통수단을 선택해주세요!");
    return;
  }

  navigator.geolocation.getCurrentPosition(position => {
    startCoords = position.coords;
    startTime = Date.now();
    document.getElementById('gps-status').textContent = '✅ 탑승 시작 위치 저장됨';
  }, () => {
    alert("위치 정보를 가져올 수 없습니다.");
  });
}


// ================= 자전거 =========================
let bikeStartCoords = null;
let bikeStartTime = null;

function startBikeTracking() {
  navigator.geolocation.getCurrentPosition(position => {
    bikeStartCoords = position.coords;
    bikeStartTime = Date.now();
    document.getElementById('bike-status').textContent = '🚲 시작 위치 저장됨';
  }, () => {
    alert("위치 정보를 가져올 수 없습니다.");
  });
}

function endBikeTracking() {
  if (!bikeStartCoords) {
    alert("먼저 '이용 시작'을 눌러주세요.");
    return;
  }

  navigator.geolocation.getCurrentPosition(position => {
    const endCoords = position.coords;
    const endTime = Date.now();
    const durationSec = (endTime - bikeStartTime) / 1000;

    const distanceKm = getDistanceFromLatLonInKm(
      bikeStartCoords.latitude, bikeStartCoords.longitude,
      endCoords.latitude, endCoords.longitude
    );

    const speed = distanceKm / (durationSec / 3600);
    const status = document.getElementById('bike-status');

    status.textContent = `🚴‍♀️ 종료 - 거리: ${distanceKm.toFixed(2)}km, 평균 속도: ${speed.toFixed(1)}km/h`;

    // 메시지 중복 방지
    if (!status.textContent.includes("경로가 저장되었습니다")) {
      status.textContent += "\n📍 경로가 저장되었습니다.";
    }
  });
}

// ================ 기록하기 버튼에만 모달 연결 ==================
document.addEventListener('DOMContentLoaded', () => {
  const buttons = document.querySelectorAll('.action-btn');
  buttons.forEach(btn => {
    btn.addEventListener('click', (e) => {
      const modalId = btn.getAttribute('data-modal');
      if (modalId) openModal(modalId);
    });
  });
});

// 실시간으로 걸음 수를 가져와서 화면 갱신
function updateStepCount() {
  fetch('/api/steps')
    .then(res => res.json())
    .then(data => {
      if (data.step_count !== undefined) {
        document.querySelector('.walk-count').textContent = `${data.step_count}보`;
      }
    });
}

// 5초마다 갱신
setInterval(updateStepCount, 5000);

function endTracking() {
  const type = document.getElementById('transport-type').value;
  if (!type) {
    alert("🚨 교통수단을 선택해주세요!");
    return;
  }

  if (!startCoords) {
    alert("먼저 '탑승 시작'을 눌러주세요.");
    return;
  }

  navigator.geolocation.getCurrentPosition(position => {
    const endCoords = position.coords;
    const endTime = Date.now();
    const durationSec = (endTime - startTime) / 1000;

    const distanceKm = getDistanceFromLatLonInKm(
      startCoords.latitude, startCoords.longitude,
      endCoords.latitude, endCoords.longitude
    );

    const speed = distanceKm / (durationSec / 3600); // km/h
    const statusBox = document.getElementById('gps-status');

    const isPublicTransport = speed >= 10 && speed <= 60;

    statusBox.textContent = isPublicTransport
      ? `🚌 ${type === "bus" ? "버스" : "지하철"} 인식됨 - 거리: ${distanceKm.toFixed(2)}km, 속도: ${speed.toFixed(1)}km/h`
      : `❌ 속도 범위 초과 - 거리: ${distanceKm.toFixed(2)}km, 속도: ${speed.toFixed(1)}km/h`;

    // ✅ 서버에 전송
    fetch('/api/transport', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ distance: distanceKm, speed: speed, transport_type: type })
    })
    .then(res => res.json())
    .then(data => {
      alert(data.message || "전송 완료");
    })
    .catch(err => {
      console.error("서버 오류", err);
      // alert("⚠️ 서버 오류 발생");
    });

    // 초기화
    startCoords = null;
    startTime = null;
  }, () => {
    alert("위치 정보를 가져올 수 없습니다.");
  });
}


// 거리 계산 함수
function getDistanceFromLatLonInKm(lat1, lon1, lat2, lon2) {
  const R = 6371;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1 * Math.PI / 180) *
    Math.cos(lat2 * Math.PI / 180) *
    Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

let bikeMap;  // 지도 객체
let bikePath; // 선 객체

function submitRecycle() {
  const fileInput = document.getElementById("recycle-photo");
  const resultBox = document.getElementById("recycle-result");
  const file = fileInput.files[0];

  if (!file) {
    alert("사진을 업로드해주세요.");
    return;
  }

  const formData = new FormData();
  formData.append("image", file);

  fetch("/predict", {
    method: "POST",
    body: formData
  })
    .then(res => res.json())
    .then(data => {
      if (data.result === "recycling") {
        resultBox.innerText = data.message || "✅ 분리배출한 것으로 인식되었습니다!";
        resultBox.style.color = "green";

        // ✅ 포인트 UI 업데이트
        if (data.point !== undefined) {
          document.getElementById("user-point").innerText = `${data.point}P`;
        }
      } else {
        resultBox.innerText = "❌ 분리배출로 인식되지 않았습니다.";
        resultBox.style.color = "red";
      }
    })

}

function endBikeTracking() {
  if (!bikeStartCoords) {
    alert("먼저 '이용 시작'을 눌러주세요.");
    return;
  }

  navigator.geolocation.getCurrentPosition(position => {
    const endCoords = position.coords;
    const endTime = Date.now();
    const durationSec = (endTime - bikeStartTime) / 1000;

    const distanceKm = getDistanceFromLatLonInKm(
      bikeStartCoords.latitude, bikeStartCoords.longitude,
      endCoords.latitude, endCoords.longitude
    );

    const speed = distanceKm / (durationSec / 3600);
    const status = document.getElementById('bike-status');

    status.textContent = `🚴‍♀️ 종료 - 거리: ${distanceKm.toFixed(2)}km, 평균 속도: ${speed.toFixed(1)}km/h`;

    fetch('/api/bike', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',  // 🔥 세션 유지 필수!
      body: JSON.stringify({ distance: distanceKm, speed: speed })
    })

    .then(res => res.json())
    .then(data => {
      console.log("서버 응답:", data);  // 👈 이 줄 추가
      if (data.message) {
        alert(data.message); // ✅ 알림창 표시
        // ✅ 포인트 UI 반영 (선택 사항)
        if (data.point !== undefined) {
          document.getElementById("user-point").innerText = `${data.point}P`;
        }
      } else {
        alert("❌ 알 수 없는 오류 발생");
      }
    })
    .catch(err => {
      console.error("서버 오류", err);
      // alert("⚠️ 서버 오류 발생");
    });

    // 초기화
    bikeStartCoords = null;
    bikeStartTime = null;
  }, () => {
    alert("위치 정보를 가져올 수 없습니다.");
  });
}
