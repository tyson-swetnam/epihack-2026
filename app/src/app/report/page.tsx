/**
 * Domain selection — pick Person / Animal / Environment (plan/08 Phase 2).
 * Each choice routes to /report/[type]. Anonymity defaults per plan/06.
 */
import Link from 'next/link';
import { ArrowRight, PawPrint, Sprout, User } from 'lucide-react';

import { AppTopBar } from '@/components/AppShell';

const choices = [
  {
    type: 'human',
    label: 'A person',
    sub: 'Illness, heat, exposure',
    Icon: User,
  },
  {
    type: 'animal',
    label: 'An animal',
    sub: 'Sick, dead, or unusual',
    Icon: PawPrint,
  },
  {
    type: 'environmental',
    label: 'The environment',
    sub: 'Sewage, smoke, water',
    Icon: Sprout,
  },
] as const;

export default function ReportPicker() {
  return (
    <>
      <AppTopBar backHref="/" title="What did you see?" />

      <section className="flex flex-col gap-3 px-4 pb-8 pt-6">
        <p className="text-sm leading-5 text-slate-600">
          Pick one. No login, no name.
        </p>

        {choices.map(({ type, label, sub, Icon }) => (
          <Link key={type} href={`/report/${type}`} className="choice-row">
            <span className="grid size-10 place-items-center rounded-md bg-soft-mint text-public-teal">
              <Icon className="size-5" aria-hidden="true" />
            </span>
            <span className="flex-1">
              <span className="block text-sm font-extrabold text-ink">
                {label}
              </span>
              <span className="block text-xs text-slate-500">{sub}</span>
            </span>
            <ArrowRight className="size-4 text-slate-400" aria-hidden="true" />
          </Link>
        ))}

        <p className="mt-2 text-xs leading-5 text-slate-500">
          Animal and Environment reports stay fully anonymous. Person reports
          are anonymous by default — you choose later whether to share contact
          details with a clinician.
        </p>
      </section>
    </>
  );
}
