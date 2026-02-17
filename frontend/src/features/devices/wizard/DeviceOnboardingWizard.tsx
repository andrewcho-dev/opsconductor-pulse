import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Stepper, type Step } from "@/components/ui/stepper";
import { Step1DeviceDetails } from "./Step1DeviceDetails";
import { Step2TagsGroups } from "./Step2TagsGroups";
import { Step3Provision } from "./Step3Provision";
import { Step4Credentials } from "./Step4Credentials";
import { Step5AlertRules } from "./Step5AlertRules";
import type { DeviceDetailsData, ProvisionResult, TagsGroupsData } from "./types";

type WizardStep = 1 | 2 | 3 | 4 | 5;

const STEPS: Step[] = [
  { id: 1, label: "Device Details" },
  { id: 2, label: "Tags & Groups" },
  { id: 3, label: "Provision" },
  { id: 4, label: "Credentials" },
  { id: 5, label: "Alert Rules" },
];

export default function DeviceOnboardingWizard() {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState<WizardStep>(1);
  const [completedSteps, setCompletedSteps] = useState<number[]>([]);
  const [step1Data, setStep1Data] = useState<DeviceDetailsData | null>(null);
  const [step2Data, setStep2Data] = useState<TagsGroupsData | null>(null);
  const [credentials, setCredentials] = useState<ProvisionResult | null>(null);

  function completeStep(stepId: number) {
    setCompletedSteps((prev) => [...new Set([...prev, stepId])]);
  }

  const combinedData = useMemo(() => {
    if (!step1Data || !step2Data) return null;
    return {
      ...step1Data,
      ...step2Data,
    };
  }, [step1Data, step2Data]);

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Device Onboarding Wizard</CardTitle>
        </CardHeader>
        <CardContent>
          <Stepper steps={STEPS} currentStep={currentStep} completedSteps={completedSteps} />
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-6">
          {currentStep === 1 && (
            <Step1DeviceDetails
              initialData={step1Data}
              onNext={(data) => {
                setStep1Data(data);
                completeStep(1);
                setCurrentStep(2);
              }}
            />
          )}

          {currentStep === 2 && (
            <Step2TagsGroups
              initialData={step2Data}
              onBack={() => setCurrentStep(1)}
              onNext={(data) => {
                setStep2Data(data);
                completeStep(2);
                setCurrentStep(3);
              }}
            />
          )}

          {currentStep === 3 && combinedData && (
            <Step3Provision
              deviceData={combinedData}
              onBack={() => setCurrentStep(2)}
              onSuccess={(creds) => {
                setCredentials(creds);
                completeStep(3);
                setCurrentStep(4);
              }}
            />
          )}

          {currentStep === 4 && credentials && (
            <Step4Credentials
              credentials={credentials}
              deviceName={step1Data?.name ?? credentials.device_id}
              onNext={() => {
                completeStep(4);
                setCurrentStep(5);
              }}
            />
          )}

          {currentStep === 5 && credentials && step1Data && (
            <Step5AlertRules
              deviceId={credentials.device_id}
              deviceType={step1Data.device_type}
              onDone={() => {
                completeStep(5);
                navigate("/devices");
              }}
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
