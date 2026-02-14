import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

export interface Step {
  id: number;
  label: string;
  description?: string;
}

interface StepperProps {
  steps: Step[];
  currentStep: number;
  completedSteps: number[];
}

export function Stepper({ steps, currentStep, completedSteps }: StepperProps) {
  return (
    <div className="w-full overflow-x-auto pb-1">
      <div className="flex min-w-max items-center gap-2">
        {steps.map((step, index) => {
          const isCurrent = step.id === currentStep;
          const isCompleted = completedSteps.includes(step.id);
          return (
            <div key={step.id} className="flex items-center gap-2">
              <div className="flex items-center gap-2">
                <div
                  className={cn(
                    "flex h-8 w-8 items-center justify-center rounded-full border text-xs font-semibold",
                    isCompleted
                      ? "border-green-600 bg-green-600 text-white"
                      : isCurrent
                      ? "border-primary bg-primary text-primary-foreground"
                      : "border-border bg-background text-muted-foreground"
                  )}
                >
                  {isCompleted ? <Check className="h-4 w-4" /> : step.id}
                </div>
                <div>
                  <div
                    className={cn(
                      "text-sm font-medium",
                      isCurrent || isCompleted ? "text-foreground" : "text-muted-foreground"
                    )}
                  >
                    {step.label}
                  </div>
                  {step.description && (
                    <div className="text-xs text-muted-foreground">{step.description}</div>
                  )}
                </div>
              </div>
              {index < steps.length - 1 && <div className="mx-2 h-px w-8 bg-border" />}
            </div>
          );
        })}
      </div>
    </div>
  );
}
