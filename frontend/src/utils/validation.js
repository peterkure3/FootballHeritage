import { z } from "zod";

// Age verification - must be 21+
const calculateAge = (dob) => {
  const birthDate = new Date(dob);
  const today = new Date();
  let age = today.getFullYear() - birthDate.getFullYear();
  const monthDiff = today.getMonth() - birthDate.getMonth();

  if (
    monthDiff < 0 ||
    (monthDiff === 0 && today.getDate() < birthDate.getDate())
  ) {
    age--;
  }

  return age;
};

// Registration schema
export const registerSchema = z
  .object({
    firstName: z
      .string()
      .min(1, "First name is required")
      .max(50, "First name must be less than 50 characters")
      .trim(),

    lastName: z
      .string()
      .min(1, "Last name is required")
      .max(50, "Last name must be less than 50 characters")
      .trim(),

    email: z
      .string()
      .email("Invalid email address")
      .min(5, "Email must be at least 5 characters")
      .max(100, "Email must be less than 100 characters")
      .toLowerCase()
      .trim(),

    password: z
      .string()
      .min(8, "Password must be at least 8 characters")
      .max(100, "Password must be less than 100 characters")
      .regex(/[A-Z]/, "Password must contain at least one uppercase letter")
      .regex(/[a-z]/, "Password must contain at least one lowercase letter")
      .regex(/[0-9]/, "Password must contain at least one number")
      .regex(
        /[^A-Za-z0-9]/,
        "Password must contain at least one special character",
      ),

    confirmPassword: z.string().min(1, "Please confirm your password"),

    dob: z
      .string()
      .min(1, "Date of birth is required")
      .refine(
        (dob) => {
          const age = calculateAge(dob);
          return age >= 21;
        },
        { message: "You must be at least 21 years old to register" },
      ),

    terms: z.boolean().refine((val) => val === true, {
      message: "You must accept the terms and conditions",
    }),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  });

// Login schema
export const loginSchema = z.object({
  email: z
    .string()
    .email("Invalid email address")
    .min(1, "Email is required")
    .toLowerCase()
    .trim(),

  password: z.string().min(1, "Password is required"),
});

// Deposit schema
export const depositSchema = z.object({
  amount: z
    .number()
    .positive("Amount must be positive")
    .min(10, "Minimum deposit is $10")
    .max(10000, "Maximum deposit is $10,000")
    .refine(
      (val) => Number.isFinite(val) && val === Math.round(val * 100) / 100,
      { message: "Amount must have at most 2 decimal places" },
    ),
});

// Withdraw schema
export const withdrawSchema = z.object({
  amount: z
    .number()
    .positive("Amount must be positive")
    .min(10, "Minimum withdrawal is $10")
    .max(10000, "Maximum withdrawal is $10,000")
    .refine(
      (val) => Number.isFinite(val) && val === Math.round(val * 100) / 100,
      { message: "Amount must have at most 2 decimal places" },
    ),
});

// Bet schema
export const betSchema = z.object({
  eventId: z
    .number()
    .int("Event ID must be an integer")
    .positive("Invalid event ID"),

  amount: z
    .number()
    .positive("Bet amount must be positive")
    .min(1, "Minimum bet is $1")
    .max(100, "Maximum bet per event is $100")
    .refine(
      (val) => Number.isFinite(val) && val === Math.round(val * 100) / 100,
      { message: "Amount must have at most 2 decimal places" },
    ),

  odds: z.number().positive("Odds must be positive"),

  type: z.enum(["moneyline", "spread", "over_under"], {
    errorMap: () => ({ message: "Invalid bet type" }),
  }),
});

// Utility function to validate and return errors
export const validateField = (schema, data) => {
  try {
    schema.parse(data);
    return { success: true, errors: {} };
  } catch (error) {
    if (error instanceof z.ZodError) {
      const errors = {};
      error.errors.forEach((err) => {
        const path = err.path.join(".");
        errors[path] = err.message;
      });
      return { success: false, errors };
    }
    return { success: false, errors: { _global: "Validation failed" } };
  }
};

// Safe parse wrapper
export const safeParse = (schema, data) => {
  return schema.safeParse(data);
};

// Helper to get age from DOB
export const getAge = calculateAge;

export default {
  registerSchema,
  loginSchema,
  depositSchema,
  withdrawSchema,
  betSchema,
  validateField,
  safeParse,
  getAge,
};
