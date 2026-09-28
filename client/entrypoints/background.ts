export default defineBackground(() => {
  // Click vào biểu tượng extension sẽ tự động mở cột SidePanel bên phải
  chrome.sidePanel
    .setPanelBehavior({ openPanelOnActionClick: true })
    .catch((error) => console.error(error));
});