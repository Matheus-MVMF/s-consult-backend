import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth"; // Adicionamos esta linha

const firebaseConfig = {
  apiKey: "AIzaSyB6uyscpg1JrzkoVwYOFC_zHPzYMY_Pyc8",
  authDomain: "teste-6f9b9.firebaseapp.com",
  projectId: "teste-6f9b9",
  storageBucket: "teste-6f9b9.firebasestorage.app",
  messagingSenderId: "806477113409",
  appId: "1:806477113409:web:e3274d193f3a13d6ddfec0",
  measurementId: "G-6GRNWM7E6E"
};

// Inicializa o Firebase
const app = initializeApp(firebaseConfig);

// EXPORTA o cadeado (auth) para o site usar
export const auth = getAuth(app);