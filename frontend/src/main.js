import { createApp } from 'vue';
import App from './App.vue';
import OpcIcon from './components/OpcIcon.vue';
import './style.css';

const app = createApp(App);
app.component('OpcIcon', OpcIcon);
app.mount('#app');
