window.alpineData = function () {
  // Keys for localStorage
  const STORAGE_KEYS = {
    collapsed: "kvp_collapsed",
    originalText: "kvp_originalText",
    segmentedText: "kvp_segmentedText",
    segmentationType: "kvp_segmentationType",
    phoneticization: "kvp_phoneticization",
    sanskritMode: "kvp_sanskritMode",
    anusvaraStyle: "kvp_anusvaraStyle",
  };

  // Helper to load from storage, fallback to default
  function load(key, fallback) {
    try {
      const val = localStorage.getItem(key);
      return val !== null ? val : fallback;
    } catch (e) {
      return fallback;
    }
  }

  const defaultText = stripIndent(`
      གང་གི་བློ་གྲོས་སྒྲིབ་གཉིས་སྤྲིན་བྲལ་ཉི་ལྟར་རྣམ་དག་རབ་གསལ་བས།།
      ཇི་སྙེད་དོན་ཀུན་ཇི་བཞིན་གཟིགས་ཕྱིར་ཉིད་ཀྱི་ཐུགས་ཀར་གླེགས་བམ་འཛིན།།
      གང་དག་སྲིད་པའི་བཙོན་རར་མ་རིག་མུན་འཐུམས་སྡུག་བསྔལ་གྱིས་གཟིར་བའི།།
      འགྲོ་ཚོགས་ཀུན་ལ་བུ་གཅིག་ལྟར་བརྩེ་ཡན་ལག་དྲུག་བཅུའི་དབྱངས་ལྡན་གསུང༌།།
      འབྲུག་ལྟར་ཆེར་སྒྲོགས་ཉོན་མོངས་གཉིད་སློང་ལས་ཀྱི་ལྕགས་སྒྲོག་འགྲོལ་མཛད་ཅིང༌།།
      མ་རིག་མུན་སེལ་སྡུག་བསྔལ་མྱུ་གུ་ཇི་སྙེད་གཅོད་མཛད་རལ་གྲི་བསྣམས།།
      གདོད་ནས་དག་ཅིང་ས་བཅུའི་མཐར་སོན་ཡོན་ཏན་ལུས་རྫོགས་རྒྱལ་སྲས་ཐུ་བོའི་སྐུ།།
      བཅུ་ཕྲག་བཅུ་དང་བཅུ་གཉིས་རྒྱན་སྤྲས་བདག་བློའི་མུན་སེལ་འཇམ་པའི་དབྱངས་ལ་རབ་ཏུ་འདུད།།
    `);
  const storedText = load(STORAGE_KEYS.originalText, defaultText);

  return {
    step: 1,
    originalText: storedText === "" ? defaultText : storedText,
    collapsed: load(STORAGE_KEYS.collapsed, "false") === "true",
    segmentedText: load(STORAGE_KEYS.segmentedText, ""),
    segmentationType: load(STORAGE_KEYS.segmentationType, "words"),
    phoneticization: load(STORAGE_KEYS.phoneticization, "kvp"),
    sanskritMode: load(STORAGE_KEYS.sanskritMode, "keep"),
    anusvaraStyle: load(STORAGE_KEYS.anusvaraStyle, "ṃ"),
    phoneticResult: null,
    showHelp: false,
    activeHelpType: "",
    copiedOriginal: false,
    copiedSegmented: false,
    copiedPhonetics: false,
    showSegmentation: false,
    showSegmented: false,
    showPhonetic: false,
    textareaHeight: 320, // Default height in pixels
    scrollSyncEnabled: true,
    windowWidth: window.innerWidth,

    get isDesktop() {
      return this.windowWidth >= 1024;
    },

    get isMobile() {
      return this.windowWidth < 1024;
    },

    async segment() {
      const formData = new FormData();
      formData.append("str", this.originalText);
      formData.append("sanskrit_mode", this.sanskritMode);
      formData.append("anusvara_style", this.anusvaraStyle);

      const endpoint =
        this.segmentationType === "words"
          ? "/segmentbywords"
          : this.segmentationType === "two"
          ? "/segmentbytwo"
          : "/segmentbyone";

      try {
        const response = await fetch(endpoint, {
          method: "POST",
          body: formData,
        });
        const data = await response.json();

        // Count trailing newlines in original text
        const originalTrailingCount = (
          this.originalText.match(/(\r?\n)*$/)[0] || ""
        ).length;

        // Process segmented text and preserve trailing newlines
        let segmentedText = data.segmented.replace(/^ +/gm, "");
        let kvpText = data.kvp;
        let ipaText = data.ipa;

        // Count current trailing newlines and adjust if needed
        const currentTrailingCount = (segmentedText.match(/(\r?\n)*$/)[0] || "")
          .length;
        if (currentTrailingCount < originalTrailingCount) {
          const missingNewlines = "\n".repeat(
            originalTrailingCount - currentTrailingCount
          );
          segmentedText += missingNewlines;
          kvpText += missingNewlines;
          ipaText += missingNewlines;
        }

        this.segmentedText = segmentedText;

        // Transform and store results
        this.phoneticResult = {
          kvp: kvptodisplay(kvpText),
          ipa: ipatodisplay(ipaText),
          advanced: ipatophon(ipaText, "advanced"),
          intermediate: ipatophon(ipaText, "intermediate"),
          simple: ipatophon(ipaText, "simple"),
        };

        this.step = 2;
        // UI state for vertical progressive flow will be handled by $watch hooks below
        // Auto-switch to KVP tab for 1 or 2 syllable segmentation
        if (
          this.segmentationType === "words" ||
          this.segmentationType === "two"
        ) {
          this.phoneticization = "kvp";
        }
      } catch (error) {
        console.error("Error:", error);
      }
    },

    init() {
      // Set up resize listener for responsive behavior with debouncing
      let resizeTimeout;
      window.addEventListener("resize", () => {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(() => {
          const previousWidth = this.windowWidth;
          this.windowWidth = window.innerWidth;

          // Force reactivity update
          this.$nextTick(() => {
            if (window.innerWidth >= 1024) {
              // Desktop: adjust textarea height based on viewport
              this.adjustTextareaHeight();
            } else if (previousWidth >= 1024 && window.innerWidth < 1024) {
              // Transitioning from desktop to mobile: auto-resize textareas to fit content
              setTimeout(() => {
                if (this.$refs.tibetanTextarea && this.originalText) {
                  this.autoResizeTextarea(this.$refs.tibetanTextarea);
                }
                if (this.$refs.segmentedTextarea && this.segmentedText) {
                  this.autoResizeTextarea(this.$refs.segmentedTextarea);
                }
              }, 50);
            }
          });
        }, 100);
      });

      // On init, load from localStorage is already handled in data above
      this.$nextTick(() => {
        // Adjust textarea heights on initialization
        this.adjustTextareaHeight();

        // Auto-resize textareas on mobile if they have content
        if (window.innerWidth < 1024) {
          // Use setTimeout to ensure DOM is fully rendered
          setTimeout(() => {
            if (this.$refs.tibetanTextarea && this.originalText) {
              this.autoResizeTextarea(this.$refs.tibetanTextarea);
            }
            if (this.$refs.segmentedTextarea && this.segmentedText) {
              this.autoResizeTextarea(this.$refs.segmentedTextarea);
            }
          }, 50);
        }

        if (this.originalText && this.originalText.trim() !== "") {
          this.segmentationType = this.segmentationType || "words";
          this.segment().then(() => {
            this.phoneticization = this.phoneticization || "kvp";
            this.phoneticize();
            // Auto-resize after content is loaded on mobile
            if (window.innerWidth < 1024) {
              setTimeout(() => {
                if (this.$refs.segmentedTextarea) {
                  this.autoResizeTextarea(this.$refs.segmentedTextarea);
                }
              }, 50);
            }
          });
        } else {
          this.segmentedText = "";
          this.phoneticResult = null;
        }
      });

      // Watch and persist fields to localStorage
      this.$watch("collapsed", (val) => {
        try {
          localStorage.setItem(STORAGE_KEYS.collapsed, val);
        } catch (e) {}
      });
      this.$watch("originalText", (val) => {
        try {
          localStorage.setItem(STORAGE_KEYS.originalText, val);
        } catch (e) {}
      });
      this.$watch("segmentedText", (val) => {
        try {
          localStorage.setItem(STORAGE_KEYS.segmentedText, val);
        } catch (e) {}
      });
      this.$watch("segmentationType", (val) => {
        try {
          localStorage.setItem(STORAGE_KEYS.segmentationType, val);
        } catch (e) {}
      });
      this.$watch("phoneticization", (val) => {
        try {
          localStorage.setItem(STORAGE_KEYS.phoneticization, val);
        } catch (e) {}
      });
      this.$watch("sanskritMode", (val) => {
        try {
          localStorage.setItem(STORAGE_KEYS.sanskritMode, val);
        } catch (e) {}
      });
      this.$watch("anusvaraStyle", (val) => {
        try {
          localStorage.setItem(STORAGE_KEYS.anusvaraStyle, val);
        } catch (e) {}
      });

      // Debounce helpers
      let segmentTimeout = null;
      let phoneticizeTimeout = null;
      const debounce = (fn, timeoutVar, ms = 120) => {
        if (timeoutVar) clearTimeout(timeoutVar);
        return setTimeout(fn, ms);
      };

      // Live: When originalText changes, segment and phoneticize
      this.$watch("originalText", (val) => {
        if (val && val.trim() !== "") {
          this.segmentationType = this.segmentationType || "words";
          segmentTimeout = debounce(() => {
            this.segment();
          }, segmentTimeout);
        } else {
          this.segmentedText = "";
          this.phoneticResult = null;
        }
      });

      // Live: When segmentedText changes, phoneticize
      this.$watch("segmentedText", (val) => {
        if (val && val.trim() !== "") {
          this.phoneticization = this.phoneticization || "kvp";
          phoneticizeTimeout = debounce(() => {
            this.phoneticize();
          }, phoneticizeTimeout);
        } else {
          this.phoneticResult = null;
        }
      });

      // Live: When phoneticization changes, re-phoneticize
      this.$watch("phoneticization", (val) => {
        if (this.segmentedText && this.segmentedText.trim() !== "") {
          this.phoneticize();
        }
      });

      // Auto-resize textareas on mobile when content changes
      this.$watch("originalText", () => {
        if (window.innerWidth < 1024) {
          this.$nextTick(() => {
            if (this.$refs.tibetanTextarea) {
              this.autoResizeTextarea(this.$refs.tibetanTextarea);
            }
          });
        }
      });

      this.$watch("segmentedText", () => {
        if (window.innerWidth < 1024) {
          this.$nextTick(() => {
            if (this.$refs.segmentedTextarea) {
              this.autoResizeTextarea(this.$refs.segmentedTextarea);
            }
          });
        }
      });
    },

    async phoneticize() {
      const formData = new FormData();
      formData.append("str", this.segmentedText);
      formData.append("sanskrit_mode", this.sanskritMode);
      formData.append("anusvara_style", this.anusvaraStyle);

      try {
        const response = await fetch("/phoneticize", {
          method: "POST",
          body: formData,
        });
        const data = await response.json();

        // Transform and store results
        this.phoneticResult = {
          kvp: kvptodisplay(data.kvp),
          ipa: ipatodisplay(data.ipa),
          advanced: ipatophon(data.ipa, "advanced"),
          intermediate: ipatophon(data.ipa, "intermediate"),
          simple: ipatophon(data.ipa, "simple"),
        };
      } catch (error) {
        console.error("Error:", error);
      }
    },

    getPhoneticResult(type) {
      if (!this.phoneticResult) {
        return "";
      }
      return this.phoneticResult[type] || "";
    },

    async copyToClipboard(text, panel = "phonetics") {
      try {
        // Convert <br/> tags to newlines before stripping HTML
        const textWithNewlines = text.replace(/<br\s*\/?>/gi, "\n");

        // Strip remaining HTML tags for clipboard
        const tempDiv = document.createElement("div");
        tempDiv.innerHTML = textWithNewlines;
        const cleanText = tempDiv.textContent || tempDiv.innerText || "";

        await navigator.clipboard.writeText(cleanText);

        // Set the correct copied state based on panel
        if (panel === "original") {
          this.copiedOriginal = true;
          setTimeout(() => (this.copiedOriginal = false), 2000);
        } else if (panel === "segmented") {
          this.copiedSegmented = true;
          setTimeout(() => (this.copiedSegmented = false), 2000);
        } else {
          this.copiedPhonetics = true;
          setTimeout(() => (this.copiedPhonetics = false), 2000);
        }
      } catch (error) {
        console.error("Error copying to clipboard:", error);
      }
    },

    // Adjust textarea heights based on device type
    adjustTextareaHeight() {
      this.$nextTick(() => {
        const isMobile = window.innerWidth < 1024;

        if (isMobile) {
          // On mobile, set height to 'auto' to allow content-based sizing
          // This will be handled by CSS with min-height
          this.textareaHeight = "auto";
          return;
        }

        // Desktop behavior: Calculate available viewport height
        const viewportHeight = window.innerHeight;

        // Account for header, margins, padding, and other UI elements
        const headerHeight = 84; // Approximate header height
        const collapseButton = 100; // Collapse button area
        const summaryDiv = 80; // Button area height when not collapsed
        const margins = 120; // Various margins and gaps

        // Calculate available height for textareas
        const availableHeight =
          viewportHeight - headerHeight - summaryDiv - margins - collapseButton;

        // Set minimum and maximum constraints
        const minHeight = 200;
        const maxHeight = Math.max(availableHeight, minHeight);

        // Ensure we don't exceed viewport bounds
        const finalHeight = Math.min(maxHeight, viewportHeight * 0.7);

        this.textareaHeight = finalHeight;
      });
    },

    // Auto-resize textareas to fit content on mobile
    autoResizeTextarea(element) {
      if (window.innerWidth < 1024 && element) {
        // Reset height to auto to get the correct scrollHeight
        element.style.height = "auto";
        // Set height to scrollHeight to fit content
        element.style.height = Math.max(element.scrollHeight, 100) + "px";
      }
    },

    // Synchronize scrolling between textareas
    syncScroll(event, source) {
      if (!this.scrollSyncEnabled) return;

      const sourceElement = event.target;
      const scrollTop = sourceElement.scrollTop;
      const scrollPercentage =
        sourceElement.scrollHeight > sourceElement.clientHeight
          ? scrollTop /
            (sourceElement.scrollHeight - sourceElement.clientHeight)
          : 0;

      // Use requestAnimationFrame for smoother sync and prevent infinite loops
      if (this.syncScrollFrame) {
        cancelAnimationFrame(this.syncScrollFrame);
      }

      this.syncScrollFrame = requestAnimationFrame(() => {
        // Temporarily disable sync to prevent infinite loops
        this.scrollSyncEnabled = false;

        // Sync with other textareas
        const targets = [];
        if (source !== "tibetan" && this.$refs.tibetanTextarea) {
          targets.push(this.$refs.tibetanTextarea);
        }
        if (source !== "segmented" && this.$refs.segmentedTextarea) {
          targets.push(this.$refs.segmentedTextarea);
        }
        if (source !== "phonetics" && this.$refs.phoneticOutput) {
          targets.push(this.$refs.phoneticOutput);
        }

        targets.forEach((target) => {
          if (target && target.scrollHeight > target.clientHeight) {
            const targetScrollTop =
              scrollPercentage * (target.scrollHeight - target.clientHeight);
            target.scrollTop = targetScrollTop;
          }
        });

        // Re-enable sync immediately after the frame
        this.scrollSyncEnabled = true;
        this.syncScrollFrame = null;
      });
    },
  };
};

const stripIndent = (str) =>
  str
    .trim()
    .split("\n")
    .map((line) => line.trim())
    .join("\n");

function ipatophon(ipa, level) {
  res = ipa.replace(/(?:\r\n|\r|\n)/g, "<br/>");
  res = res.replace(/y/g, "ü");
  res = res.replace(/c/g, "ky");
  if (level == "advanced") {
    res = res.replace(/ɔ([\u0304\u0331])?/g, "<span class='gray'>o$1</span>");
    res = res.replace(/ə([\u0304\u0331])?/g, "<span class='gray'>a$1</span>");
    res = res.replace(/3/g, "<span class='gray'>ʰ</span>");
    res = res.replace(/ʔ([kp])\u031A/g, "<sub>$1</sub>");
    res = res.replace(/ʔ/g, "<sub>ʔ</sub>");
    res = res.replace(/n\u031A/g, "n");
  } else if (level == "intermediate") {
    res = res.replace(/[̱̄3˥˦˧˨˩]/g, "");
    res = res.replace(/ʔ([kp])\u031A/g, "<sub>$1</sub>");
    res = res.replace(/ʔ/g, "<sub>ʔ</sub>");
    res = res.replace(/ɔ/g, "o");
    res = res.replace(/ə/g, "<span class='gray'>a</span>");
    res = res.replace(/n\u031A/g, "n");
  } else {
    res = res.replace(/[̱̄3ʰʔ\u031Aː˥˦˧˨˩]/g, "");
    res = res.replace(/ɔ/g, "o");
    res = res.replace(/ə/g, "a");
    res = res.replace(/n\u031A/g, "n");
  }
  res = res.replace(/ɣ/g, "g");
  res = res.replace(/[̥̊]/g, ""); // half-voicing, not displayed
  res = res.replace(/ɖ/g, "ḍ");
  res = res.replace(/ʈ/g, "ṭ");
  res = res.replace(/ɲ/g, "ny");
  res = res.replace(/ø/g, "ö");
  res = res.replace(/ɟ/g, "gy");
  res = res.replace(/j/g, "y");
  res = res.replace(/ɛ/g, "è");
  res = res.replace(/e/g, "é");
  res = res.replace(/ŋ(\s)/g, "ng$1");
  res = res.replace(/ŋ/g, "ṅ");
  res = res.replace(/tɕ/g, "ch");
  res = res.replace(/ɕ/g, "sh");
  res = res.replace(/dʑ/g, "j");
  res = res.replace(/dz/g, "z");
  return res;
}

function ipatodisplay(ipa) {
  res = ipa.replace(/(?:\r\n|\r|\n)/g, "<br/>");
  res = res.replace(/3/g, "<span class='gray'>ʰ</span>");
  return res;
}

function kvptodisplay(kvp) {
  res = kvp.replace(/(?:\r\n|\r|\n)/g, "<br/>");
  return res;
}
