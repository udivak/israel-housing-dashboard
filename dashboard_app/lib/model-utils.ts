/** Strip the "owner/" prefix for UI display. The full id stays in API calls. */
export function modelDisplayName(id: string): string {
  const slash = id.indexOf("/");
  return slash >= 0 ? id.slice(slash + 1) : id;
}
