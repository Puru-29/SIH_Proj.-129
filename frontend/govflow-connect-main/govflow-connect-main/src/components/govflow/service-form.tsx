import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import type { ServiceFormField, ServiceFormSchema } from "@/lib/api";

type FormValue = string | boolean;
type FormValues = Record<string, FormValue>;

type Props = {
  schema: ServiceFormSchema;
  values: FormValues;
  onChange: (field: ServiceFormField, value: FormValue) => void;
};

function isVisible(field: ServiceFormField, values: FormValues) {
  return !field.visible_if || values[field.visible_if.field] === field.visible_if.equals;
}

function Field({ field, values, onChange }: { field: ServiceFormField; values: FormValues; onChange: Props["onChange"] }) {
  if (!isVisible(field, values)) return null;
  const value = values[field.id] ?? "";

  if (field.type === "checkbox") {
    return <label className="flex items-start gap-3 rounded-lg border border-border p-3 text-sm"><Checkbox checked={value === true} onCheckedChange={(checked) => onChange(field, checked === true)} /><span><span className="font-medium">{field.label}</span>{field.help_text ? <span className="mt-1 block text-xs text-muted-foreground">{field.help_text}</span> : null}</span></label>;
  }

  if (field.type === "select") {
    return <div className="space-y-2"><Label htmlFor={`service-${field.id}`}>{field.label}</Label><select id={`service-${field.id}`} className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm" value={String(value)} onChange={(event) => onChange(field, event.target.value)} required={field.required}><option value="">Select {field.label.toLowerCase()}</option>{(field.options || []).map((option) => <option key={option} value={option}>{option}</option>)}</select>{field.help_text ? <p className="text-xs text-muted-foreground">{field.help_text}</p> : null}</div>;
  }

  const dateLimits = field.type === "date" ? { min: "1900-01-01", max: new Date().toISOString().slice(0, 10) } : {};
  return <div className="space-y-2"><Label htmlFor={`service-${field.id}`}>{field.label}</Label><Input id={`service-${field.id}`} type={field.type} inputMode={field.type === "number" || field.type === "tel" ? "numeric" : undefined} value={String(value)} onChange={(event) => onChange(field, event.target.value)} required={field.required} maxLength={field.max_length} pattern={field.pattern} {...dateLimits} />{field.help_text ? <p className="text-xs text-muted-foreground">{field.help_text}</p> : null}</div>;
}

export function ServiceForm({ schema, values, onChange }: Props) {
  return <div className="space-y-5"><div className="rounded-lg border border-primary/20 bg-primary/5 px-3 py-2 text-sm font-semibold text-primary">{schema.service_name}</div>{schema.sections.map((section) => { const fields = section.fields.filter((field) => field.required || field.visible_if); return fields.length ? <section key={section.id} className="space-y-3"><div><h3 className="text-sm font-semibold">{section.label}</h3>{section.description ? <p className="mt-1 text-xs text-muted-foreground">{section.description}</p> : null}</div><div className="grid gap-4 sm:grid-cols-2">{fields.map((field) => <Field key={field.id} field={field} values={values} onChange={onChange} />)}</div></section> : null; })}</div>;
}
