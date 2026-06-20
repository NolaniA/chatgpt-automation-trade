// ======================================
// Mini Playwright - helper.js
// For Chrome DevTools Console
// ======================================

window.page = (() => {

  // ---------- utils ----------
  const sleep = ms => new Promise(r => setTimeout(r, ms));

  // ---------- wait ----------
  const waitForSelector = (selector, timeout = 10000) => {
    return new Promise((resolve, reject) => {
      const el = document.querySelector(selector);
      if (el) return resolve(el);

      const observer = new MutationObserver(() => {
        const el = document.querySelector(selector);
        if (el) {
          observer.disconnect();
          resolve(el);
        }
      });

      observer.observe(document.body, { childList: true, subtree: true });

      setTimeout(() => {
        observer.disconnect();
        reject(`Timeout waiting for selector: ${selector}`);
      }, timeout);
    });
  };

  const waitForVisible = async (selector, timeout = 10000) => {
    const el = await waitForSelector(selector, timeout);
    const start = Date.now();

    while (Date.now() - start < timeout) {
      const style = window.getComputedStyle(el);
      if (
        style.display !== "none" &&
        style.visibility !== "hidden" &&
        el.offsetHeight > 0
      ) {
        return el;
      }
      await sleep(100);
    }
    throw `Timeout waiting for visible: ${selector}`;
  };

  const waitForCount = async (selector, count = 1, timeout = 10000) => {
    const start = Date.now();
    while (Date.now() - start < timeout) {
      const els = document.querySelectorAll(selector);
      if (els.length == count) return els;
      await sleep(100);
    }
    throw `Timeout waiting for count: ${selector}`;
  };

  const waitForText = async (selector, text, timeout = 10000) => {
    const el = await waitForSelector(selector, timeout);
    const start = Date.now();

    while (Date.now() - start < timeout) {
      if (el.innerText.includes(text)) return el;
      await sleep(100);
    }
    throw `Timeout waiting for text: ${text}`;
  };

  const waitForDisappear = async (selector, timeout = 10000) => {
    const start = Date.now();
    while (Date.now() - start < timeout) {
      if (!document.querySelector(selector)) return true;
      await sleep(100);
    }
    throw `Timeout waiting for disappear: ${selector}`;
  };

  // ---------- actions ----------
  const click = async (selector) => {
    const el = await waitForVisible(selector);
    el.scrollIntoView({ behavior: "smooth", block: "center" });
    el.click();
  };

  const fill = async (selector, value) => {
    const el = await waitForVisible(selector);
    el.focus();

    const setter = Object.getOwnPropertyDescriptor(
      el.tagName === "TEXTAREA"
        ? HTMLTextAreaElement.prototype
        : HTMLInputElement.prototype,
      "value"
    ).set;

    setter.call(el, value);
    el.dispatchEvent(new Event("input", { bubbles: true }));
  };

  const press = async (key) => {
    document.activeElement.dispatchEvent(
      new KeyboardEvent("keydown", {
        bubbles: true,
        key,
        code: key
      })
    );
  };

  // ---------- locator ----------
  const locator = (selector) => ({
    count: () => document.querySelectorAll(selector).length,
    first: () => document.querySelector(selector),
    all: () => [...document.querySelectorAll(selector)],
    click: () => click(selector),
    fill: (v) => fill(selector, v)
  });

  // ---------- scroll ----------
  const scroll = async (step = 800, delay = 800, times = 1) => {
    for (let i = 0; i < times; i++) {
      window.scrollBy(0, step);
      await sleep(delay);
    }
  };

  const scrollToBottom = async () => {
    window.scrollTo({
      top: document.body.scrollHeight,
      behavior: "smooth"
    });
  };

  const scrollUntilCount = async (
    selector,
    targetCount,
    step = 800,
    delay = 1000
  ) => {
    let prev = 0;

    while (true) {
      const curr = document.querySelectorAll(selector).length;
      if (curr >= targetCount) return curr;
      if (curr === prev) return curr;

      prev = curr;
      window.scrollBy(0, step);
      await sleep(delay);
    }
  };

  // ---------- misc ----------
  const retry = async (fn, times = 3) => {
    for (let i = 0; i < times; i++) {
      try {
        return await fn();
      } catch (e) {
        if (i === times - 1) throw e;
      }
    }
  };

  const getAttribute = (selector, attributeName) => {
    const el = document.querySelector(selector);
    if (!el) return null;
    return el.getAttribute(attributeName);
  };

  // ---------- file upload helpers ----------

  /**
   * เปิด file picker แล้ว resolve เป็น Array<File>
   * ใช้ได้ทุกเว็บเพราะสร้าง input ชั่วคราวเอง
   */
  const pickFiles = ({ multiple = false, accept = "" } = {}) => {
    return new Promise((resolve, reject) => {
      const input = document.createElement("input");
      input.type = "file";
      input.multiple = multiple;
      if (accept) input.accept = accept;
      input.style.display = "none";
      document.body.appendChild(input);

      const cleanup = () => input.remove();

      input.addEventListener(
        "change",
        () => {
          const files = [...(input.files || [])];
          cleanup();
          resolve(files);
        },
        { once: true }
      );

      // ถ้าผู้ใช้กดยกเลิก จะไม่มี change event ในหลายๆกรณี
      // เลยใช้ blur + timeout เป็น fallback
      input.addEventListener(
        "blur",
        () => {
          setTimeout(() => {
            if (!input.files || input.files.length === 0) {
              cleanup();
              reject("File picker canceled");
            }
          }, 300);
        },
        { once: true }
      );

      input.click();
    });
  };

  /**
   * ใส่ไฟล์ให้ <input type="file"> ด้วย DataTransfer แล้ว dispatch change
   */
  const setInputFiles = async (inputSelector, files) => {
    const el = await waitForVisible(inputSelector);
    if (!el || el.tagName !== "INPUT" || el.type !== "file") {
      throw `Target is not <input type="file"> : ${inputSelector}`;
    }

    const dt = new DataTransfer();
    (files || []).forEach((f) => dt.items.add(f));

    // บาง browser ยอมให้ assign ตรงๆ บางอันต้อง defineProperty
    try {
      el.files = dt.files;
    } catch (e) {
      Object.defineProperty(el, "files", {
        value: dt.files,
        writable: false
      });
    }

    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));

    return [...el.files];
  };

  /**
   * ตัวเดียวจบ:
   * - ถ้า selector เป็น input[type=file] => click แล้วรอ change
   * - ถ้า selector ไม่ใช่ input[type=file] => เปิด picker แล้วเอาไฟล์ไป set ให้ inputSelector ที่ส่งมา
   *
   * ใช้แบบ:
   *   await page.uploadFile('input[type=file]')
   * หรือ
   *   await page.uploadFile('#realFileInput', { accept: 'image/*' })
   */
  const uploadFile = async (inputSelector, opts = {}) => {
    const { multiple = false, accept = "" } = opts;

    const el = document.querySelector(inputSelector);
    if (el && el.tagName === "INPUT" && el.type === "file") {
      // ให้ผู้ใช้เลือกไฟล์ผ่าน input ตัวนี้เลย
      el.scrollIntoView({ behavior: "smooth", block: "center" });

      const files = await new Promise((resolve, reject) => {
        const onChange = () => resolve([...(el.files || [])]);
        el.addEventListener("change", onChange, { once: true });

        // fallback ถ้ากดยกเลิก
        setTimeout(() => {
          // ถ้าไม่มีไฟล์ก็ถือว่ายกเลิก/ไม่เลือก
          if (!el.files || el.files.length === 0) reject("File picker canceled");
        }, 15000);
      });

      return files;
    }

    // ไม่เจอ input file หรือเป็น element อื่น -> เปิด picker แล้วผูกให้ inputSelector
    const files = await pickFiles({ multiple, accept });
    await setInputFiles(inputSelector, files);
    return files;
  };

  /**
   * ส่งไฟล์ใส่ dropzone ด้วย drag&drop event
   * (ใช้ได้กับพวก UI ที่รับลากไฟล์วางแทน input)
   */
  const dropFiles = async (dropSelector, files) => {
    const el = await waitForVisible(dropSelector);

    const dt = new DataTransfer();
    (files || []).forEach((f) => dt.items.add(f));

    const fire = (type) => {
      const evt = new DragEvent(type, {
        bubbles: true,
        cancelable: true,
        dataTransfer: dt
      });
      el.dispatchEvent(evt);
    };

    el.scrollIntoView({ behavior: "smooth", block: "center" });
    fire("dragenter");
    fire("dragover");
    fire("drop");

    return true;
  };



  // ---------- expose ----------
  return {
    // wait
    waitForSelector,
    waitForVisible,
    waitForCount,
    waitForText,
    waitForDisappear,

    // actions
    click,
    fill,
    press,

    // locator
    locator,
    getAttribute,

    // scroll
    scroll,
    scrollToBottom,
    scrollUntilCount,

    // utils
    waitForTimeout: sleep,
    retry,

    // files
    pickFiles,
    setInputFiles,
    uploadFile,
    dropFiles,

  };
})();

console.log("✅ Mini Playwright helper.js loaded");

