import type { ReactNode } from "react";

export type Lang = "en" | "fr";

const STORAGE_KEY = "ta_lang";

/** Pick the initial language: saved choice → browser language → English. */
export function detectLang(): Lang {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === "en" || saved === "fr") return saved;
  } catch {
    /* localStorage may be unavailable */
  }
  const nav = (navigator.languages?.[0] ?? navigator.language ?? "en").toLowerCase();
  return nav.startsWith("fr") ? "fr" : "en";
}

export function saveLang(lang: Lang): void {
  try {
    localStorage.setItem(STORAGE_KEY, lang);
  } catch {
    /* ignore */
  }
}

export interface Strings {
  intro: string;
  helpSummary: string;
  helpSteps: ReactNode[];
  helpPrivacy: string;
  labelAthleteId: string;
  labelApiKey: string;
  labelStart: string;
  labelEnd: string;
  labelFcm: string;
  labelLthr: string;
  ariaFetchIntervals: string;
  textFetchIntervals: string;
  submitIdle: string;
  submitRunning: string;
  doneMsg: string;
  progressLogLabel: string;
  languageLabel: string;
  errAthleteId: string;
  errApiKey: string;
  errDates: string;
  errLthr: string;
  errUnexpected: string;
}

const settingsLink = "https://intervals.icu/settings";

export const translations: Record<Lang, Strings> = {
  en: {
    intro:
      "Enter your Intervals.icu credentials to download your training data (JSON). Nothing is stored — your key is used only for this run and discarded.",
    helpSummary: "Where do I find my Athlete ID and API key?",
    helpSteps: [
      <>
        Open your{" "}
        <a href={settingsLink} target="_blank" rel="noopener noreferrer">
          Intervals.icu settings
        </a>{" "}
        (log in first) and scroll to the bottom, to the <strong>Developer Settings</strong> section.
      </>,
      <>
        <strong>Athlete ID</strong> — shown there as <code>i123456</code>. Enter only the digits,
        without the leading <code>i</code> (e.g. <code>123456</code>).
      </>,
      <>
        <strong>API key</strong> — click <em>“API Key”</em> to reveal it, then copy the token and
        paste it below.
      </>,
    ],
    helpPrivacy:
      "Your API key is private — treat it like a password. It’s sent over this connection only to run your analysis and is never saved.",
    labelAthleteId: "Athlete ID",
    labelApiKey: "API key",
    labelStart: "Start date",
    labelEnd: "End date",
    labelFcm: "FCM (max HR)",
    labelLthr: "LTHR (threshold HR)",
    ariaFetchIntervals: "Fetch intervals",
    textFetchIntervals: "Include interval breakdown (slower)",
    submitIdle: "Generate & download",
    submitRunning: "Generating…",
    doneMsg: "Done — your download should have started.",
    progressLogLabel: "progress log",
    languageLabel: "Language",
    errAthleteId: "Athlete ID must be 3–9 digits (no leading 'i').",
    errApiKey: "API key looks invalid.",
    errDates: "End date must not be before start date.",
    errLthr: "LTHR must be below FCM.",
    errUnexpected: "Unexpected error",
  },
  fr: {
    intro:
      "Entrez vos identifiants Intervals.icu pour télécharger vos données d’entraînement (JSON). Rien n’est enregistré — votre clé n’est utilisée que pour cette analyse, puis supprimée.",
    helpSummary: "Où trouver mon Athlete ID et ma clé API ?",
    helpSteps: [
      <>
        Ouvrez vos{" "}
        <a href={settingsLink} target="_blank" rel="noopener noreferrer">
          paramètres Intervals.icu
        </a>{" "}
        (connectez-vous d’abord) et faites défiler tout en bas, jusqu’à la section{" "}
        <strong>Developer Settings</strong>.
      </>,
      <>
        <strong>Athlete ID</strong> — affiché sous la forme <code>i123456</code>. Saisissez
        uniquement les chiffres, sans le <code>i</code> initial (ex. <code>123456</code>).
      </>,
      <>
        <strong>Clé API</strong> — cliquez sur <em>« API Key »</em> pour l’afficher, puis copiez le
        jeton et collez-le ci-dessous.
      </>,
    ],
    helpPrivacy:
      "Votre clé API est privée — traitez-la comme un mot de passe. Elle n’est transmise via cette connexion que pour lancer votre analyse et n’est jamais enregistrée.",
    labelAthleteId: "Athlete ID",
    labelApiKey: "Clé API",
    labelStart: "Date de début",
    labelEnd: "Date de fin",
    labelFcm: "FCM (FC max)",
    labelLthr: "LTHR (FC seuil)",
    ariaFetchIntervals: "Récupérer les intervalles",
    textFetchIntervals: "Inclure la décomposition par intervalles (plus lent)",
    submitIdle: "Générer et télécharger",
    submitRunning: "Génération…",
    doneMsg: "Terminé — votre téléchargement devrait avoir démarré.",
    progressLogLabel: "journal de progression",
    languageLabel: "Langue",
    errAthleteId: "L’Athlete ID doit comporter 3 à 9 chiffres (sans le « i » initial).",
    errApiKey: "La clé API semble invalide.",
    errDates: "La date de fin ne doit pas précéder la date de début.",
    errLthr: "Le LTHR doit être inférieur à la FCM.",
    errUnexpected: "Erreur inattendue",
  },
};
