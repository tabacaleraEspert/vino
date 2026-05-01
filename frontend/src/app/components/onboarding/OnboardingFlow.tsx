import { useState, useCallback } from "react";
import { useNavigate } from "react-router";
import { useAuth } from "../../context/AuthContext";
import { apiFetch } from "../../../lib/api";

import { OnboardingStyles } from "./primitives";
import { ScreenWelcome } from "./screens/ScreenWelcome";
import { ScreenCategories } from "./screens/ScreenCategories";
import { ScreenBudget } from "./screens/ScreenBudget";
import { ScreenGmailConnect } from "./screens/ScreenGmailConnect";
import { ScreenTourDashboard } from "./screens/ScreenTourDashboard";
import { ScreenTourCard } from "./screens/ScreenTourCard";
import { ScreenTourWhatsApp } from "./screens/ScreenTourWhatsApp";
import { ScreenWhatsAppConnect } from "./screens/ScreenWhatsAppConnect";
import { ScreenDone } from "./screens/ScreenDone";

// Steps: Welcome → Categories → Budget → Gmail → TourDashboard → TourCard → TourWhatsApp → WhatsAppConnect → Done
const TOTAL_STEPS = 9;

export function OnboardingFlow() {
  const [step, setStep] = useState(() => {
    const saved = localStorage.getItem("onboarding_step");
    return saved ? Math.min(parseInt(saved, 10), TOTAL_STEPS - 1) : 0;
  });
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  const { user, markOnboardingDone } = useAuth();

  const goNext = useCallback(() => {
    setStep((s) => {
      const next = s + 1;
      localStorage.setItem("onboarding_step", String(next));
      return next;
    });
  }, []);

  const handleBudget = useCallback(async (income: number) => {
    if (isLoading) return;
    setIsLoading(true);
    try {
      const today = new Date();
      const mes = `${String(today.getMonth() + 1).padStart(2, "0")}/${String(today.getFullYear() % 100).padStart(2, "0")}`;
      await apiFetch("/presupuestos/auto-assign", {
        method: "POST",
        body: JSON.stringify({ total: income, mes_anio: mes }),
      });
    } catch (e) {
      console.error("Auto-assign failed:", e);
    }
    setIsLoading(false);
    goNext();
  }, [goNext, isLoading]);

  const handleGmail = useCallback(async (authCode: string | null) => {
    if (authCode) {
      try {
        await apiFetch("/gmail/connect", {
          method: "POST",
          body: JSON.stringify({ code: authCode }),
        });
      } catch (e) {
        console.error("Gmail connect failed:", e);
      }
    }
    goNext();
  }, [goNext]);

  const handleWhatsApp = useCallback(async (phoneNumber: string | null) => {
    if (isLoading) return;
    setIsLoading(true);
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
    setIsLoading(false);
    goNext();
  }, [goNext, isLoading]);

  const handleFinish = useCallback(async () => {
    if (isLoading) return;
    setIsLoading(true);
    try {
      await apiFetch("/auth/onboarding", { method: "PATCH" });
    } catch (e) {
      console.error("Mark onboarding complete failed:", e);
    }
    markOnboardingDone();
    localStorage.removeItem("onboarding_step");
    navigate("/", { replace: true });
  }, [navigate, markOnboardingDone, isLoading]);

  const firstName = user?.name?.split(" ")[0] || "amig@";

  return (
    <>
      <OnboardingStyles />
      {step === 0 && <ScreenWelcome onNext={goNext} name={firstName} />}
      {step === 1 && <ScreenCategories onNext={goNext} />}
      {step === 2 && <ScreenBudget onNext={handleBudget} isLoading={isLoading} />}
      {step === 3 && <ScreenGmailConnect onNext={handleGmail} />}
      {step === 4 && <ScreenTourDashboard onNext={goNext} />}
      {step === 5 && <ScreenTourCard onNext={goNext} />}
      {step === 6 && <ScreenTourWhatsApp onNext={goNext} />}
      {step === 7 && <ScreenWhatsAppConnect onNext={handleWhatsApp} />}
      {step === 8 && <ScreenDone onFinish={handleFinish} />}
    </>
  );
}
