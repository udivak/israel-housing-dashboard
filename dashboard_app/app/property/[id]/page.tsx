import { PropertyClient } from "@/components/property/PropertyClient";

export default async function PropertyPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <PropertyClient id={id} />;
}
