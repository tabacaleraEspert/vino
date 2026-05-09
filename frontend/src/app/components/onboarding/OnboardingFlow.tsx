import { useState, useCallback, useEffect } from "react";
import { useNavigate } from "react-router";
import { useAuth } from "../../context/AuthContext";
import { apiFetch } from "../../../lib/api";

import { OnboardingStyles } from "./primitives";
import { ScreenWelcome } from "./screens/ScreenWelcome";
import { ScreenBudgetTheory } from "./screens/ScreenBudgetTheory";
import { ScreenCategories } from "./screens/ScreenCategories";
import { ScreenBudget } from "./screens/ScreenBudget";
import { ScreenGmailConnect } from "./screens/ScreenGmailConnect";
import { ScreenTourDashboard } from "./screens/ScreenTourDashboard";
import { ScreenTourCard } from "./screens/ScreenTourCard";
import { ScreenTourWhatsApp } from "./screens/ScreenTourWhatsApp";
import { ScreenWhatsAppConnect } from "./screens/ScreenWhatsAppConnect";
import { ScreenDone } from "./screens/ScreenDone";

// Steps: Welcome → BudgetTheory → Categories → Budget → TourCard → Gmail → TourDashboard → TourWhatsApp → WhatsAppConnect → Done
const TOTAL_STEPS = 10;

export function OnboardingFlow() {
  const [step, setStep] = useState(() => {
    const saved = localStorage.getItem("onboarding_step");
    return saved ? Math.min(parseInt(saved, 10), TOTAL_STEPS - 1) : 0;
  });
  const [isLoading, setIsLoading] = useState(false);
  const [stepLoaded, setStepLoaded] = useState(false);
  const navigate = useNavigate();
  const { user, markOnboardingDone } = useAuth();

  // Load step from backend on mount (overrides localStorage if higher)
  useEffect(() => {
    (async () => {
      try {
        const res = await apiFetch<{ step: number }>("/auth/onboarding/step");
        const backendStep = res.step || 0;
        const localStep = parseInt(localStorage.getItem("onboarding_step") || "0", 10);
        const resolved = Math.max(backendStep, localStep);
        if (resolved > 0 && resolved < TOTAL_STEPS) {
          setStep(resolved);
          localStorage.setItem("onboarding_step", String(resolved));
        }
      } catch {}
      setStepLoaded(true);
    })();
  }, []);

  const persistStep = useCallback((nextStep: number) => {
    localStorage.setItem("onboarding_step", String(nextStep));
    // Fire and forget — don't block UI
    apiFetch("/auth/onboarding/step", {
      method: "PATCH",
      body: JSON.stringify({ step: nextStep }),
    }).catch(() => {});
  }, []);

  const goNext = useCallback(() => {
    setStep((s) => {
      const next = s + 1;
      persistStep(next);
      return next;
    });
  }, [persistStep]);

  const goBack = useCallback(() => {
    setStep((s) => {
      const prev = Math.max(0, s - 1);
      persistStep(prev);
      return prev;
    });
  }, [persistStep]);

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

  const handleWhatsApp = useCallback((_phoneNumber: string | null) => {
    // Phone is already saved by the OTP verification flow in ScreenWhatsAppConnect
    goNext();
  }, [goNext]);

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
      {step === 1 && <ScreenBudgetTheory onNext={goNext} onBack={goBack} />}
      {step === 2 && <ScreenCategories onNext={goNext} onBack={goBack} />}
      {step === 3 && <ScreenBudget onNext={handleBudget} onBack={goBack} isLoading={isLoading} />}
      {step === 4 && <ScreenTourCard onNext={goNext} onBack={goBack} />}
      {step === 5 && <ScreenGmailConnect onNext={handleGmail} onBack={goBack} />}
      {step === 6 && <ScreenTourDashboard onNext={goNext} onBack={goBack} />}
      {step === 7 && <ScreenTourWhatsApp onNext={goNext} onBack={goBack} />}
      {step === 8 && <ScreenWhatsAppConnect onNext={handleWhatsApp} onBack={goBack} />}
      {step === 9 && <ScreenDone onFinish={handleFinish} onBack={goBack} />}
    </>
  );
}
