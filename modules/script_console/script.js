(async () => {
  location.hash = "script=RUNNING";

  const sleep = (ms) => new Promise(r => setTimeout(r, ms));

  // ✅ รอ spinner หาย (แก้จาก waitForCount(...,0) ที่มันผ่านทันที)
  // ถ้าเว็บมึงมี spinner selector นี้จริงก็ใช้ได้
  // ถ้าไม่ใช่ ให้เปลี่ยน selector ให้ตรง
  try {
    await page.waitForDisappear('circle[stroke="currentColor"]', 20000);
  } catch (e) {
    console.log("spinner not disappeared (continue anyway):", e);
  }

  // click submit
  let sendBtn = null;

  for (let i = 1; i <= 100; i++) {
    sendBtn = document.querySelector('button[data-testid="send-button"]');
    if (sendBtn) break;

    console.log(`รอบที่ ${i} ยังไม่เจอ รอต่อ...`);
    await new Promise(r => setTimeout(r, 500));
  }

  if (!sendBtn) return console.log("not found send button");
  sendBtn.click();
  console.log('click send');

  // wait until result is complete
  await new Promise((resolve, reject) => {
    console.log('wait result');
    const timeout = setTimeout(() => {
      clearInterval(interval);
      reject(new Error("Timeout waiting for result"));
    }, 10 * 60 * 1000); // 10 minutes

    const interval = setInterval(() => {
      const stopButton = document.querySelector('button[data-testid="stop-button"]');

      if (!stopButton) {
        clearInterval(interval);
        clearTimeout(timeout);
        resolve();
      }
    }, 500);
  });
  // wait result success
  //await new Promise((resolve) => {
    //let interval = setInterval(() => {
      //if (!document.querySelector('button[data-testid="stop-button"]')) {
        //clearInterval(interval);
        //resolve();
      //}
    //}, 50000);
  //});


  sleep(1000);


  console.log("done");

  // ✅ ดึงผล (พยายามหลายแบบ)
  let jsonText = null;

  // แบบเดิมของมึง
  let preCode = null;

  for (let i = 1; i <= 10; i++) {
    preCode = document.querySelector('div#code-block-viewer div.cm-scroller pre.cm-content');
    if (preCode) break;

    console.log(`รอบที่ ${i} ยังไม่เจอcode block รอต่อ...`);
    await new Promise(r => setTimeout(r, 500));
  }

  if (!preCode) {
    throw new Error("ครบ 10 ครั้งแล้วยังไม่เจอ div#code-block-viewer div.cm-content");
  }

  console.log("เจอแล้ว:", preCode);
  if (preCode?.innerText) jsonText = preCode.innerText.trim();

  // fallback: หาข้อความใน pre/code ล่าสุด
  if (!jsonText) {
    const codes = [...document.querySelectorAll("pre code")];
    const last = codes.at(-1);
    if (last?.innerText) jsonText = last.innerText.trim();
  }

  if (!jsonText) return console.log("not found any result text");

  console.log(jsonText);

  // parse JSON
  let parsed = jsonText;
  try {
    parsed = JSON.parse(jsonText);
  } catch {
    console.log("response is not valid JSON, saving as text");
  }

  const blob = new Blob(
    [typeof parsed === "string" ? parsed : JSON.stringify(parsed, null, 2)],
    { type: "application/json" }
  );

  const blobUrl = URL.createObjectURL(blob);

  const a = document.createElement("a");
  a.href = blobUrl;
  a.download = "gpt_result.json";
  document.body.appendChild(a);
  a.click();

  // ✅ หน่วงก่อน revoke กันโหลดไม่ทัน
  // await sleep(1500);
  URL.revokeObjectURL(blobUrl);
  a.remove();

  location.hash = "script=DONE";

})();
