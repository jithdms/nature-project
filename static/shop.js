
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('success') === '1') {
    alert('교환 신청이 완료되었습니다.');
  }
