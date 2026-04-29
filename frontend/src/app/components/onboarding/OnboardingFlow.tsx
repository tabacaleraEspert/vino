import { useState, useCallback } from "react";
import { useNavigate } from "react-router";
import { useAuth } from "../../context/AuthContext";
import { apiFetch } from "../../../lib/api";
import { OnboardingStyles } from "./primitives";
import { ScreenWelcome } from "./screens/ScreenWelcome";
import { ScreenCategories } from "./screens/ScreenCategories";
import { ScreenBudget } from "./screens/ScreenBudget";
import { ScreenTourDashboard } from "./screens/ScreenTourDashboard";
import { ScreenTourCard } from "./screens/ScreenTourCard";
import { ScreenTourWhatsApp } from "./screens/ScreenTourWhatsApp";
import { ScreenWhatsAppConnect } from "./screens/ScreenWhatsAppConnect";
import { ScreenDone } from "./screens/ScreenDone";

// Steps: Welcome → Categories → Budget → TourDashboard → TourCard → TourWhatsApp → WhatsAppConnect → Done
// ScreenGmail is skipped (user already authenticated via Login page)
const TOTAL_STEPS = 8;

export function OnboardingFlow() {
  const [step, setStep] = useState(() => {
    const saved = localStorage.getItem("onboarding_step");
    return saved ? Math.min(parseInt(saved, 10), TOTAL_STEPS - 1) : 0;
  });
  const navigate = useNavigate();
  const { user } = useAuth();

  const goNext = useCallback(() => {
    setStep((s) => {
      const next = s + 1;
      localStorage.setItem("onboarding_step", String(next));
      return next;
    });
  }, []);

  const handleBudget = useCallback(async (income: number) => {
    // Call auto-assign to create budgets with 50/30/20 rule
    try {
      const today = new Date();
      const mes = `${String(today.getMonth() + 1).padStart(2, "0")}/${String(today.getFullYear() % 100).padStart(2, "0")}`;
      await apiFetch("/presupuestos/auto-assign", {
        method: "POST",
        body: JSON.stringify({ total: income, mes_anio: mes }),
      });
    } catch (e) {
      console.error("Auto-assign failed:", e);
      // Non-blocking — continue onboarding even if this fails
    }
    goNext();
  }, [goNext]);

  const handleWhatsApp = useCallback(async (phoneNumber: string | null) => {
    if (phoneNumber) {
      try {
        await apiFetch("/auth/profile", {
          method: "PATCH",
          body: JSON.stringify({ whatsapp: phoneNumber }),
        });
      } catch (e) {
        console.error("WhatsApp connect failed:", e);
      }
    }
    goNext();
  }, [goNext]);

  const handleFinish = useCallback(async () => {
    try {
      await apiFetch("/auth/onboarding", { method: "PATCH" });
    } catch (e) {
      console.error("Mark onboarding complete failed:", e);
    }
    localStorage.removeItem("onboarding_step");
    navigate("/", { replace: true });
  }, [navigate]);

  const firstName = user?.name?.split(" ")[0] || "amig@";

  return (
    <>
      <OnboardingStyles />
      {step === 0 && <ScreenWelcome onNext={goNext} name={firstName} />}
      {step === 1 && <ScreenCategories onNext={goNext} />}
      {step === 2 && <ScreenBudget onNext={handleBudget} />}
      {step === 3 && <ScreenTourDashboard onNext={goNext} />}
      {step === 4 && <ScreenTourCard onNext={goNext} />}
      {step === 5 && <ScreenTourWhatsApp onNext={goNext} />}
      {step === 6 && <ScreenWhatsAppConnect onNext={handleWhatsApp} />}
      {step === 7 && <ScreenDone onFinish={handleFinish} />}
    </>
  );
}
