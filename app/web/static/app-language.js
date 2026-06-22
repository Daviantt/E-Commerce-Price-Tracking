(() => {
  const LANGUAGE_KEY = "lapwiseLanguage";

  const translations = {
    vi: {
      languageControl: "Language",
      languageName: "VI",
      switchLanguageTitle: "Chuyển sang tiếng Anh",
      navHome: "⌂ Trang chủ",
      navProducts: "▦ Danh sách sản phẩm",
      navDashboard: "◈ Dashboard sản phẩm",
      navFavorites: "♥ Sản phẩm yêu thích",
      sideBrands: "Thương hiệu",
      loggedIn: "Đang đăng nhập",
      login: "Đăng nhập",
      logout: "Đăng xuất",
      backToProducts: "← Quay lại danh sách",
      productDashboardEyebrow: "Product dashboard",
      productDashboardTitle: "Dashboard sản phẩm",
      noDataTitle: "Chưa có dữ liệu",
      noDataCopy: "Hãy import dữ liệu hoặc chạy crawler trước.",
      saveFavorite: "♡ Lưu yêu thích",
      productImagePending: "Ảnh sản phẩm sẽ được thêm khi có crawler hình ảnh.",
      chatPanelTitle: "Chat tư vấn sản phẩm",
      chatWelcome: "xin chào tôi có thể giúp gì cho bạn?",
      chatSuggestionsLabel: "Câu hỏi gợi ý",
      chatBestPrice: "Giá rẻ nhất",
      chatBuyToday: "Có nên mua?",
      chatTrend: "Xu hướng giá",
      chatCompareShops: "So sánh shop",
      chatConfig: "Cấu hình",
      chatStock: "Kho hàng",
      chatBestQuestion: "Giá rẻ nhất ở đâu?",
      chatBuyQuestion: "Có nên mua hôm nay không?",
      chatTrendQuestion: "Xu hướng giá gần đây thế nào?",
      chatCompareQuestion: "So sánh giá các cửa hàng",
      chatConfigQuestion: "Cấu hình máy này thế nào?",
      chatStockQuestion: "Máy này còn hàng không?",
      chatPlaceholder: "Hỏi: máy này giá ở đâu rẻ nhất?",
      send: "Gửi",
      lowestPrice: "Giá thấp nhất",
      averagePrice: "Giá trung bình",
      averagePriceCopy: "Tính trên website có kinh doanh",
      dealerCompare: "So sánh giá đại lý",
      currencySwitcherLabel: "Đổi tiền tệ",
      priceTrend: "Xu hướng giá",
      dealerBestCurrent: "Giá tốt nhất hiện tại",
      dealerAvailable: "Đang kinh doanh",
      dealerUnavailable: "Website này không kinh doanh model này",
      badgeLowest: "Rẻ nhất",
      notAvailable: "Không kinh doanh",
      historyEmpty: "Chưa đủ lịch sử giá để phân tích xu hướng",
      currentPrice: "Giá hiện tại",
      latestMovement: "Gần nhất",
      comparedWith: "So với",
      previousPoint: "mốc trước",
      fromStart: "Từ đầu kỳ",
      historyLow: "Thấp nhất",
      historyHigh: "Cao nhất",
      date: "Ngày",
      lowestPriceHeader: "Giá thấp nhất",
      change: "Thay đổi",
      decrease: "Giảm",
      increase: "Tăng",
      unchanged: "Không đổi",
      chatLoading: "Đang phân tích dữ liệu sản phẩm...",
      chatFallback: "Không lấy được câu trả lời.",
      chatConnectError: "Không kết nối được chatbot. Vui lòng thử lại sau.",
      favoriteSaved: "Đã lưu sản phẩm yêu thích.",
      favoriteSaveError: "Không lưu được.",
      specsPriceTitle: "Thông số & nhận định giá",
      specsEmpty: "Chưa có thông số chi tiết",
      priceInsightTitle: "Nhận định giá",
      priceInsightNoData: "Chưa đủ dữ liệu để phân tích giá.",
      priceInsightNoPrice: "Chưa có giá bán hợp lệ để phân tích.",
      priceInsightSpread: "Giá giữa các shop đang chênh khoảng {percent}%, nên ưu tiên nơi có giá thấp nhất.",
      priceInsightDiscount: "Mức giảm tốt nhất hiện khoảng {percent}% so với giá gốc.",
      priceInsightStable: "Giá giữa các shop khá sát nhau, nên kiểm tra thêm bảo hành và tình trạng hàng.",
      priceSpreadLabel: "Chênh lệch giữa shop",
      priceBestDiscountLabel: "Mức giảm tốt nhất",
      segmentBudget: "Phổ thông",
      segmentMainstream: "Tầm trung",
      segmentUpperMid: "Cận cao cấp",
      segmentPremium: "Cao cấp",
      segmentUnknown: "Chưa xếp hạng",
      specStorage: "Ổ cứng",
      specScreenSize: "Màn hình",
      specResolution: "Độ phân giải",
      specRefreshRate: "Tần số quét",
      specOs: "Hệ điều hành",
      specWeight: "Trọng lượng",
      specBattery: "Pin",
      authLoginMode: "Đăng nhập",
      authRegisterMode: "Đăng ký",
      authLoginTitle: "Đăng nhập",
      authRegisterTitle: "Tạo tài khoản",
      authLoginSubtitle: "Đăng nhập để lưu và theo dõi sản phẩm yêu thích.",
      authRegisterSubtitle: "Tài khoản local dùng để lưu sản phẩm yêu thích.",
      authDisplayName: "Tên hiển thị",
      authEmail: "Email",
      authPassword: "Mật khẩu",
      authLoginButton: "Đăng nhập",
      authRegisterButton: "Tạo tài khoản",
      authHasAccount: "Đã có tài khoản?",
      authNoAccount: "Chưa có tài khoản?",
      authLoginLink: "Đăng nhập",
      authRegisterLink: "Tạo tài khoản",
      authProcessingError: "Không thể xử lý yêu cầu.",
      authSuccess: "Thành công. Đang chuyển hướng...",
      productCatalogEyebrow: "Product catalog",
      productCatalogTitle: "Danh sách sản phẩm laptop",
      productCatalogCopy: "Chọn một sản phẩm để mở dashboard riêng, xem so sánh giá theo đại lý, lịch sử giá và hỏi assistant về model đó.",
      productSearchPlaceholder: "Tìm model, mã máy, thương hiệu...",
      brandSelectLabel: "Hãng",
      allBrands: "Tất cả",
      search: "Tìm kiếm",
      productCountLabel: "sản phẩm",
      filterFrom: "Giá từ",
      filterTo: "Giá đến",
      noLimit: "Không giới hạn",
      filterPrice: "Lọc giá",
      clearFilters: "Xoá bộ lọc",
      priceFrom: "Giá từ",
      bestRetailer: "Tốt nhất",
      followFavorite: "♡ Theo dõi / Yêu thích",
      savedFollowing: "Đã theo dõi",
      favoriteSaveProductError: "Không lưu được sản phẩm.",
      noProductTitle: "Không tìm thấy sản phẩm",
      noProductCopy: "Thử đổi từ khoá hoặc bỏ lọc thương hiệu.",
      savedProductsEyebrow: "Saved products",
      favoritesTitle: "Sản phẩm yêu thích",
      favoritesCopy: "Các model bạn đã lưu để theo dõi sau.",
      backToDashboard: "Quay lại dashboard",
      noFavoritesTitle: "Chưa có sản phẩm yêu thích",
      noFavoritesCopy: "Vào dashboard, chọn model và bấm “Lưu yêu thích”.",
      removeSaved: "Bỏ lưu",
    },
    en: {
      languageControl: "Language",
      languageName: "EN",
      switchLanguageTitle: "Switch to Vietnamese",
      navHome: "⌂ Home",
      navProducts: "▦ Products",
      navDashboard: "◈ Product dashboard",
      navFavorites: "♥ Favorites",
      sideBrands: "Brands",
      loggedIn: "Signed in",
      login: "Login",
      logout: "Log out",
      backToProducts: "← Back to products",
      productDashboardEyebrow: "Product dashboard",
      productDashboardTitle: "Product dashboard",
      noDataTitle: "No data yet",
      noDataCopy: "Import data or run the crawler first.",
      saveFavorite: "♡ Save favorite",
      productImagePending: "Product image will appear when the image crawler has data.",
      chatPanelTitle: "Product advisor chat",
      chatWelcome: "hello, how can I help you?",
      chatSuggestionsLabel: "Suggested questions",
      chatBestPrice: "Best price",
      chatBuyToday: "Buy today?",
      chatTrend: "Price trend",
      chatCompareShops: "Compare shops",
      chatConfig: "Specs",
      chatStock: "Stock",
      chatBestQuestion: "Where is the best price?",
      chatBuyQuestion: "Should I buy today?",
      chatTrendQuestion: "How has the price moved recently?",
      chatCompareQuestion: "Compare prices across shops",
      chatConfigQuestion: "What are the specs of this laptop?",
      chatStockQuestion: "Is this laptop in stock?",
      chatPlaceholder: "Ask: where is this laptop cheapest?",
      send: "Send",
      lowestPrice: "Lowest price",
      averagePrice: "Average price",
      averagePriceCopy: "Calculated from retailers currently selling it",
      dealerCompare: "Retailer price comparison",
      currencySwitcherLabel: "Change currency",
      priceTrend: "Price trend",
      dealerBestCurrent: "Best current price",
      dealerAvailable: "Available",
      dealerUnavailable: "This retailer does not sell this model",
      badgeLowest: "Lowest",
      notAvailable: "Not available",
      historyEmpty: "Not enough price history to analyze the trend",
      currentPrice: "Current price",
      latestMovement: "Latest change",
      comparedWith: "Compared with",
      previousPoint: "previous point",
      fromStart: "Since start",
      historyLow: "Lowest",
      historyHigh: "Highest",
      date: "Date",
      lowestPriceHeader: "Lowest price",
      change: "Change",
      decrease: "Down",
      increase: "Up",
      unchanged: "Unchanged",
      chatLoading: "Analyzing product data...",
      chatFallback: "Could not get an answer.",
      chatConnectError: "Could not connect to the chatbot. Please try again later.",
      favoriteSaved: "Favorite product saved.",
      favoriteSaveError: "Could not save.",
      specsPriceTitle: "Specs & Price Insight",
      specsEmpty: "No detailed specs yet",
      priceInsightTitle: "Price Insight",
      priceInsightNoData: "Not enough data to analyze price yet.",
      priceInsightNoPrice: "No valid selling price to analyze yet.",
      priceInsightSpread: "Prices differ by about {percent}% across shops, so prioritize the lowest valid offer.",
      priceInsightDiscount: "The best discount is currently about {percent}% off the original price.",
      priceInsightStable: "Retailer prices are close, so check warranty and stock status too.",
      priceSpreadLabel: "Shop price gap",
      priceBestDiscountLabel: "Best discount",
      segmentBudget: "Budget",
      segmentMainstream: "Mainstream",
      segmentUpperMid: "Upper mid-range",
      segmentPremium: "Premium",
      segmentUnknown: "Unrated",
      specStorage: "Storage",
      specScreenSize: "Screen size",
      specResolution: "Resolution",
      specRefreshRate: "Refresh rate",
      specOs: "Operating system",
      specWeight: "Weight",
      specBattery: "Battery",
      authLoginMode: "Login",
      authRegisterMode: "Register",
      authLoginTitle: "Login",
      authRegisterTitle: "Create account",
      authLoginSubtitle: "Login to save and track favorite products.",
      authRegisterSubtitle: "Local account for saving favorite products.",
      authDisplayName: "Display name",
      authEmail: "Email",
      authPassword: "Password",
      authLoginButton: "Login",
      authRegisterButton: "Create account",
      authHasAccount: "Already have an account?",
      authNoAccount: "No account yet?",
      authLoginLink: "Login",
      authRegisterLink: "Create account",
      authProcessingError: "Could not process the request.",
      authSuccess: "Success. Redirecting...",
      productCatalogEyebrow: "Product catalog",
      productCatalogTitle: "Laptop products",
      productCatalogCopy: "Choose a product to open its dashboard, compare retailer prices, inspect price history, and ask the assistant about that model.",
      productSearchPlaceholder: "Search model, code, or brand...",
      brandSelectLabel: "Brand",
      allBrands: "All",
      search: "Search",
      productCountLabel: "products",
      filterFrom: "From",
      filterTo: "To",
      noLimit: "No limit",
      filterPrice: "Filter price",
      clearFilters: "Clear filters",
      priceFrom: "From",
      bestRetailer: "Best",
      followFavorite: "♡ Watch / Favorite",
      savedFollowing: "Watching",
      favoriteSaveProductError: "Could not save product.",
      noProductTitle: "No products found",
      noProductCopy: "Try another keyword or clear the brand filter.",
      savedProductsEyebrow: "Saved products",
      favoritesTitle: "Favorite products",
      favoritesCopy: "Models you saved for later price tracking.",
      backToDashboard: "Back to dashboard",
      noFavoritesTitle: "No favorite products yet",
      noFavoritesCopy: "Open the dashboard, choose a model, and click “Save favorite”.",
      removeSaved: "Remove",
    },
  };

  function normalizeLanguage(language) {
    return translations[language] ? language : "vi";
  }

  function getLanguage() {
    return normalizeLanguage(localStorage.getItem(LANGUAGE_KEY) || "vi");
  }

  function dictionaryFor(language = getLanguage()) {
    return translations[normalizeLanguage(language)] || translations.vi;
  }

  function t(key) {
    const dictionary = dictionaryFor();
    return dictionary[key] || translations.vi[key] || key;
  }

  function setFromDictionary(nodes, dictionary, attribute, setter) {
    nodes.forEach((node) => {
      const key = node.dataset[attribute];
      if (dictionary[key]) setter(node, dictionary[key]);
    });
  }

  function applyLanguage(language) {
    const nextLanguage = normalizeLanguage(language);
    const dictionary = dictionaryFor(nextLanguage);

    document.documentElement.lang = nextLanguage === "en" ? "en" : "vi";
    setFromDictionary(document.querySelectorAll("[data-i18n]"), dictionary, "i18n", (node, value) => {
      node.textContent = value;
    });
    setFromDictionary(document.querySelectorAll("[data-i18n-html]"), dictionary, "i18nHtml", (node, value) => {
      node.innerHTML = value;
    });
    setFromDictionary(document.querySelectorAll("[data-i18n-placeholder]"), dictionary, "i18nPlaceholder", (node, value) => {
      node.placeholder = value;
    });
    setFromDictionary(document.querySelectorAll("[data-i18n-title]"), dictionary, "i18nTitle", (node, value) => {
      node.title = value;
    });
    setFromDictionary(document.querySelectorAll("[data-i18n-aria-label]"), dictionary, "i18nAriaLabel", (node, value) => {
      node.setAttribute("aria-label", value);
    });
    setFromDictionary(document.querySelectorAll("[data-i18n-message]"), dictionary, "i18nMessage", (node, value) => {
      node.dataset.message = value;
    });

    document.querySelectorAll("[data-language-toggle]").forEach((button) => {
      const label = button.querySelector("[data-language-label]") || button.querySelector("span");
      const code = button.querySelector("[data-language-code]") || button.querySelector("strong");
      if (label) label.textContent = dictionary.languageControl;
      if (code) code.textContent = dictionary.languageName;
      button.title = dictionary.switchLanguageTitle;
      button.setAttribute("aria-label", dictionary.switchLanguageTitle);
    });

    localStorage.setItem(LANGUAGE_KEY, nextLanguage);
    window.dispatchEvent(new CustomEvent("lapwise:languagechange", {
      detail: {language: nextLanguage},
    }));
  }

  function toggleLanguage() {
    applyLanguage(getLanguage() === "vi" ? "en" : "vi");
  }

  function initLanguage() {
    applyLanguage(getLanguage());
    document.querySelectorAll("[data-language-toggle]").forEach((button) => {
      if (button.dataset.languageBound === "true") return;
      button.dataset.languageBound = "true";
      button.addEventListener("click", toggleLanguage);
    });
  }

  window.LapWiseLanguage = {
    apply: applyLanguage,
    get: getLanguage,
    t,
    translations,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initLanguage);
  } else {
    initLanguage();
  }
})();
