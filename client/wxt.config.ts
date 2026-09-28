import { defineConfig } from 'wxt';

export default defineConfig({
  modules: ['@wxt-dev/module-react'],
  manifest: {
    name: 'Smart Price Assistant',
    description: 'Trợ lý so sánh giá và thẩm định bất động sản thời gian thực bằng AI',
    version: '1.0.0',
    permissions: ['activeTab', 'sidePanel', 'storage', 'scripting'],
    host_permissions: ['http://127.0.0.1:8000/*'],
    action: {
      default_title: 'Mở Smart Price Assistant'
    },
    side_panel: {
      default_path: 'sidepanel.html'
    }
  }
});