export function getScPosColor(pos: number): string {
  if (pos <= 3) return 'text-green-600 font-bold';
  if (pos <= 10) return 'text-yellow-600 font-semibold';
  if (pos <= 20) return 'text-orange-500';
  return 'text-red-500';
}

export function getScPotentialColor(potential: number): string {
  if (potential >= 2000) return 'text-green-700 font-bold';
  if (potential >= 800) return 'text-green-600 font-semibold';
  if (potential >= 300) return 'text-yellow-700';
  return 'text-slate-500';
}

export function isCtrLow(ctr: number, pos: number): boolean {
  return ctr < 2 && pos <= 10;
}
