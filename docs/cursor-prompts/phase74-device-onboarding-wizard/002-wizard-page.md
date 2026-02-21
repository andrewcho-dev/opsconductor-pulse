# Prompt 002 — Wizard Page + Orchestration

Read `frontend/src/features/devices/wizard/Step1DeviceDetails.tsx` (just created).
Read `frontend/src/components/ui/stepper.tsx` (just created).

## Create `frontend/src/features/devices/wizard/DeviceOnboardingWizard.tsx`

This is the main orchestration component at route `/devices/wizard`.

```typescript
type WizardStep = 1 | 2 | 3 | 4 | 5;

const STEPS = [
  { id: 1, label: "Device Details" },
  { id: 2, label: "Tags & Groups" },
  { id: 3, label: "Provision" },
  { id: 4, label: "Credentials" },
  { id: 5, label: "Alert Rules" },
];

export function DeviceOnboardingWizard() {
  const [currentStep, setCurrentStep] = useState<WizardStep>(1);
  const [completedSteps, setCompletedSteps] = useState<number[]>([]);
  const [step1Data, setStep1Data] = useState<DeviceDetailsData | null>(null);
  const [step2Data, setStep2Data] = useState<TagsGroupsData | null>(null);
  const [credentials, setCredentials] = useState<ProvisionResult | null>(null);

  const navigate = useNavigate();

  const handleStep1Next = (data: DeviceDetailsData) => {
    setStep1Data(data);
    setCompletedSteps(prev => [...new Set([...prev, 1])]);
    setCurrentStep(2);
  };

  // ... handlers for each step

  const handleDone = () => {
    navigate('/devices');  // return to device list
  };

  return (
    <div>
      <Stepper steps={STEPS} currentStep={currentStep} completedSteps={completedSteps} />
      <div className="wizard-content">
        {currentStep === 1 && <Step1DeviceDetails onNext={handleStep1Next} initialData={step1Data} />}
        {currentStep === 2 && <Step2TagsGroups onNext={handleStep2Next} onBack={() => setCurrentStep(1)} />}
        {currentStep === 3 && <Step3Provision deviceData={combinedData} onSuccess={handleProvisioned} onBack={() => setCurrentStep(2)} />}
        {currentStep === 4 && credentials && <Step4Credentials credentials={credentials} deviceName={step1Data?.name} onNext={() => setCurrentStep(5)} />}
        {currentStep === 5 && <Step5AlertRules deviceId={credentials?.device_id} deviceType={step1Data?.device_type} onDone={handleDone} />}
      </div>
    </div>
  );
}
```

## Acceptance Criteria

- [ ] DeviceOnboardingWizard.tsx orchestrates all 5 steps
- [ ] State passed between steps correctly
- [ ] Stepper shows progress
- [ ] On completion, navigates to /devices
- [ ] `npm run build` passes
