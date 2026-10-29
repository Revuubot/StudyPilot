import React from 'react';
import { render, screen } from '@testing-library/react';
import { expect, test, vi } from 'vitest';
import App from '../../App';
import api from '../../api';

// Mock the API
vi.mock('../../api', () => ({
  default: {
    isAuthenticated: vi.fn(),
    logout: vi.fn(),
  },
}));

test('renders login screen when not authenticated', () => {
  api.isAuthenticated.mockReturnValue(false);
  render(<App />);
  expect(screen.getByText(/Sign In/i)).toBeDefined();
  expect(screen.getByPlaceholderText(/you@university.edu/i)).toBeDefined();
});

test('renders navigation when authenticated', () => {
  api.isAuthenticated.mockReturnValue(true);
  render(<App />);
  expect(screen.getByText(/Summarise/i)).toBeDefined();
  expect(screen.getByText(/Ask/i)).toBeDefined();
  expect(screen.getByText(/Search/i)).toBeDefined();
  expect(screen.getByText(/Analytics/i)).toBeDefined();
});
