'use client';

import { useState } from 'react';
import { Dna, ArrowRight, Github } from 'lucide-react';
import Link from 'next/link';

export default function AuthPage() {
  const [isSignIn, setIsSignIn] = useState(true);

  return (
    <main className="flex flex-col items-center justify-center py-16 px-4">
      <div className="w-full max-w-md rounded-lg border border-zinc-800 bg-zinc-900/50 p-8 shadow-bio backdrop-blur-md">
        <div className="flex flex-col items-center mb-8">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-cyan-400/30 bg-cyan-400/10 text-cyan-300 mb-4">
            <Dna className="h-7 w-7" />
          </div>
          <h1 className="text-2xl font-semibold tracking-normal text-white">
            {isSignIn ? 'Welcome back' : 'Create an account'}
          </h1>
          <p className="mt-2 text-center text-sm text-zinc-400">
            {isSignIn 
              ? 'Enter your credentials to access your workspace' 
              : 'Start your journey with GeneGenie today'}
          </p>
        </div>

        <div className="flex rounded-md bg-zinc-950/50 p-1 mb-8 border border-zinc-800">
          <button
            onClick={() => setIsSignIn(true)}
            className={`flex-1 rounded-md py-2 text-sm font-medium transition ${
              isSignIn ? 'bg-zinc-800 text-white shadow-sm' : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            Sign In
          </button>
          <button
            onClick={() => setIsSignIn(false)}
            className={`flex-1 rounded-md py-2 text-sm font-medium transition ${
              !isSignIn ? 'bg-zinc-800 text-white shadow-sm' : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            Sign Up
          </button>
        </div>

        <form className="flex flex-col gap-4" onSubmit={(e) => e.preventDefault()}>
          {!isSignIn && (
            <div className="flex flex-col gap-1.5">
              <label htmlFor="name" className="text-sm font-medium text-zinc-300">Full Name</label>
              <input 
                type="text" 
                id="name" 
                placeholder="Dr. Jane Doe"
                className="rounded-md border border-zinc-800 bg-zinc-950/60 px-3 py-2.5 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-cyan-400/60 focus:outline-none focus:ring-1 focus:ring-cyan-400/60 transition"
              />
            </div>
          )}
          
          <div className="flex flex-col gap-1.5">
            <label htmlFor="email" className="text-sm font-medium text-zinc-300">Email Address</label>
            <input 
              type="email" 
              id="email" 
              placeholder="jane@organization.edu"
              className="rounded-md border border-zinc-800 bg-zinc-950/60 px-3 py-2.5 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-cyan-400/60 focus:outline-none focus:ring-1 focus:ring-cyan-400/60 transition"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between">
              <label htmlFor="password" className="text-sm font-medium text-zinc-300">Password</label>
              {isSignIn && (
                <a href="#" className="text-xs text-cyan-400 hover:text-cyan-300 transition">Forgot password?</a>
              )}
            </div>
            <input 
              type="password" 
              id="password" 
              placeholder="••••••••"
              className="rounded-md border border-zinc-800 bg-zinc-950/60 px-3 py-2.5 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-cyan-400/60 focus:outline-none focus:ring-1 focus:ring-cyan-400/60 transition"
            />
          </div>

          <button 
            type="submit" 
            className="mt-2 flex w-full items-center justify-center gap-2 rounded-md bg-cyan-300 px-4 py-2.5 text-sm font-semibold text-zinc-950 transition hover:bg-cyan-200"
          >
            {isSignIn ? 'Sign In to Workspace' : 'Create Account'}
            <ArrowRight className="h-4 w-4" />
          </button>
        </form>

        <div className="my-6 flex items-center">
          <div className="flex-grow border-t border-zinc-800"></div>
          <span className="mx-4 text-xs text-zinc-500">OR CONTINUE WITH</span>
          <div className="flex-grow border-t border-zinc-800"></div>
        </div>

        <button 
          type="button" 
          className="flex w-full items-center justify-center gap-2 rounded-md border border-zinc-800 bg-zinc-950/50 px-4 py-2.5 text-sm font-medium text-zinc-300 transition hover:bg-zinc-800 hover:text-white"
        >
          <Github className="h-4 w-4" />
          GitHub
        </button>

      </div>
    </main>
  );
}
