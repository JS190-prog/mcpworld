function createMcpWorldSupportForm() {
  const form = FormApp.create('MCP World 설치/연결 문의');
  form.setDescription('GitHub 계정이 없어도 MCP World 설치, 로그인, Agent 연결, 도구 호출 문제를 보낼 수 있는 문의 폼입니다.');
  form.setCollectEmail(true);
  form.setAllowResponseEdits(true);
  form.setConfirmationMessage('문의가 접수되었습니다. 확인 후 순차적으로 답변드리겠습니다.');

  form.addTextItem()
    .setTitle('이름 또는 닉네임')
    .setRequired(false);

  form.addMultipleChoiceItem()
    .setTitle('문의 유형')
    .setChoiceValues(['설치 문제', '로그인 문제', 'Agent 연결', 'MCP 도구 호출', '결제/플랜', '기능 제안', '기타'])
    .setRequired(true);

  form.addMultipleChoiceItem()
    .setTitle('사용 중인 OS')
    .setChoiceValues(['Windows 11', 'Windows 10', '기타'])
    .setRequired(true);

  form.addCheckboxItem()
    .setTitle('문제가 발생한 도구')
    .setChoiceValues(['Word', 'PowerPoint', 'Excel', 'CAD/ZWCAD', 'HWP', 'Photoshop', 'Blender', 'Local Code', 'OpenCrab', '해당 없음'])
    .setRequired(false);

  form.addParagraphTextItem()
    .setTitle('문제 설명')
    .setHelpText('어떤 상황에서 문제가 발생했는지 가능한 자세히 적어주세요.')
    .setRequired(true);

  form.addParagraphTextItem()
    .setTitle('오류 메시지 또는 화면 내용')
    .setRequired(false);

  form.addParagraphTextItem()
    .setTitle('재현 단계')
    .setHelpText('예: 1. 로그인 2. Word 연결 클릭 3. 오류 발생')
    .setRequired(false);

  form.addTextItem()
    .setTitle('첨부 파일 링크')
    .setHelpText('Google Drive, OneDrive 등 공유 링크가 있으면 입력해주세요. 민감한 파일은 공유하지 마세요.')
    .setRequired(false);

  form.addCheckboxItem()
    .setTitle('개인정보 처리 동의')
    .setChoiceValues(['문의 응대를 위해 입력 정보를 확인하는 데 동의합니다.'])
    .setRequired(true);

  Logger.log('Edit URL: ' + form.getEditUrl());
  Logger.log('Public URL: ' + form.getPublishedUrl());
}
