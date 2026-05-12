import '@testing-library/jest-dom';

// Mock NextAuth session
jest.mock('next-auth/react', () => ({
  useSession: jest.fn(() => ({
    data: {
      user: { name: 'Test User', email: 'test@example.com' },
      accessToken: 'mock-access-token',
    },
    status: 'authenticated',
  })),
  signIn: jest.fn(),
  signOut: jest.fn(),
  session: {
    user: { name: 'Test User', email: 'test@example.com' },
    accessToken: 'mock-access-token',
  },
}));

// Mock environment variables
process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000';

// Mock Sonner toast
jest.mock('sonner', () => ({
  toast: {
    success: jest.fn(),
    error: jest.fn(),
    info: jest.fn(),
    warning: jest.fn(),
  },
}));

// Mock window.location
delete window.location;
window.location = { href: '', pathname: '/' };

// Mock fetch
global.fetch = jest.fn();