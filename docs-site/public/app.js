const header = document.querySelector("[data-header]");
const progress = document.querySelector("[data-scroll-progress]");
const toast = document.querySelector("[data-toast]");
const menuToggle = document.querySelector("[data-menu-toggle]");
const searchDialog = document.querySelector("[data-search-dialog]");
const searchInput = document.querySelector("[data-search-input]");
const searchResults = document.querySelector("[data-search-results]");
const searchIndexNode = document.getElementById("search-index");
const searchIndex = searchIndexNode ? JSON.parse(searchIndexNode.textContent || "[]") : [];
let toastTimer;
let activeSearchIndex = -1;

const showToast = (message = "已复制到剪贴板") => {
  if (!toast) return;
  toast.textContent = message;
  toast.classList.add("visible");
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => toast.classList.remove("visible"), 1600);
};

const copyText = async (text) => {
  try {
    await navigator.clipboard.writeText(text);
    showToast();
  } catch {
    showToast("浏览器未允许复制，请手动选择文本");
  }
};

document.querySelectorAll("[data-copy]").forEach((button) => {
  button.addEventListener("click", () => {
    copyText(button.dataset.copy);
    const label = button.querySelector("[data-copy-label]");
    if (label) {
      label.textContent = "已复制";
      window.setTimeout(() => (label.textContent = "复制"), 1600);
    }
  });
});

document.querySelectorAll("pre").forEach((block) => {
  if (block.closest(".hero-code")) return;
  const wrapper = document.createElement("div");
  wrapper.className = "generated-code-block";
  block.before(wrapper);
  wrapper.append(block);
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = "复制";
  button.setAttribute("aria-label", "复制代码");
  button.addEventListener("click", () => copyText(block.innerText.trim()));
  wrapper.append(button);
});

const updateScroll = () => {
  const current = window.scrollY;
  const max = document.documentElement.scrollHeight - window.innerHeight;
  const isDocs = document.body.classList.contains("docs-page");
  header?.classList.toggle("scrolled", isDocs || current > window.innerHeight * 0.72);
  if (progress) progress.style.width = `${max > 0 ? (current / max) * 100 : 0}%`;
};

window.addEventListener("scroll", updateScroll, { passive: true });
updateScroll();

const closeMenu = () => {
  document.body.classList.remove("menu-open");
  menuToggle?.setAttribute("aria-expanded", "false");
};

menuToggle?.addEventListener("click", () => {
  const open = document.body.classList.toggle("menu-open");
  menuToggle.setAttribute("aria-expanded", String(open));
});
document.querySelectorAll("[data-docs-nav] a").forEach((link) => link.addEventListener("click", closeMenu));

const themeToggle = document.querySelector("[data-theme-toggle]");
const themeLabel = document.querySelector("[data-theme-label]");
const savedTheme = localStorage.getItem("ormate-docs-theme");
if (savedTheme) document.documentElement.dataset.theme = savedTheme;

const syncThemeLabel = () => {
  if (themeLabel) themeLabel.textContent = document.documentElement.dataset.theme === "dark" ? "浅色阅读" : "深色阅读";
};
syncThemeLabel();

themeToggle?.addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  localStorage.setItem("ormate-docs-theme", next);
  syncThemeLabel();
});

const openSearch = () => {
  if (!searchDialog || !searchInput) return;
  if (!searchDialog.open) searchDialog.showModal();
  searchInput.value = "";
  renderSearch("");
  window.setTimeout(() => searchInput.focus(), 30);
};

const closeSearch = () => {
  if (searchDialog?.open) searchDialog.close();
  activeSearchIndex = -1;
};

const renderSearch = (query) => {
  if (!searchResults) return;
  const normalized = query.trim().toLowerCase();
  if (!normalized) {
    searchResults.innerHTML = "<p>输入关键词开始搜索文档。</p>";
    activeSearchIndex = -1;
    return;
  }
  const matches = searchIndex
    .filter((item) => `${item.title} ${item.kicker} ${item.description}`.toLowerCase().includes(normalized))
    .slice(0, 8);
  if (!matches.length) {
    searchResults.innerHTML = "<p>没有找到匹配内容。</p>";
    activeSearchIndex = -1;
    return;
  }
  searchResults.innerHTML = matches
    .map(
      (item, index) =>
        `<a class="search-result${index === activeSearchIndex ? " active" : ""}" href="${item.url}" data-search-result><strong>${item.title}</strong><span>${item.description}</span></a>`,
    )
    .join("");
};

document.querySelectorAll("[data-search-open]").forEach((button) => button.addEventListener("click", openSearch));
searchInput?.addEventListener("input", () => {
  activeSearchIndex = -1;
  renderSearch(searchInput.value);
});
searchDialog?.addEventListener("click", (event) => {
  if (event.target === searchDialog) closeSearch();
});

document.addEventListener("keydown", (event) => {
  const isTyping = ["INPUT", "TEXTAREA"].includes(document.activeElement?.tagName);
  if (event.key === "/" && !isTyping && !searchDialog?.open) {
    event.preventDefault();
    openSearch();
    return;
  }
  if (event.key === "Escape" && searchDialog?.open) {
    closeSearch();
    return;
  }
  if (!searchDialog?.open || !["ArrowDown", "ArrowUp", "Enter"].includes(event.key)) return;
  const results = [...document.querySelectorAll("[data-search-result]")];
  if (!results.length) return;
  event.preventDefault();
  if (event.key === "Enter" && activeSearchIndex >= 0) {
    results[activeSearchIndex].click();
    return;
  }
  const direction = event.key === "ArrowDown" ? 1 : -1;
  activeSearchIndex = (activeSearchIndex + direction + results.length) % results.length;
  renderSearch(searchInput.value);
});

if (window.matchMedia("(prefers-reduced-motion: no-preference)").matches) {
  const revealObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.animate(
          [
            { opacity: 0, transform: "translateY(26px)" },
            { opacity: 1, transform: "translateY(0)" },
          ],
          { duration: 620, easing: "cubic-bezier(.22, 1, .36, 1)", fill: "both" },
        );
        revealObserver.unobserve(entry.target);
      });
    },
    { threshold: 0.08 },
  );
  document.querySelectorAll(".doc-section > *, .docs-index-list > a").forEach((element) => revealObserver.observe(element));
}
