const result = (connector, detail) => ({ connector, ok: true, detail });

export const connectors = {
  aadhaar: { verify: async () => result("Aadhaar sandbox", "Identity matched") },
  education: { verify: async () => result("Education sandbox", "Enrollment and marks verified") },
  revenue: { verify: async () => result("Revenue sandbox", "Income certificate verified") },
  landRecords: { verify: async () => result("Land Records sandbox", "No conflicting land record") },
  pfms: { verify: async () => result("PFMS sandbox", "Bank account ready for benefit transfer") },
};