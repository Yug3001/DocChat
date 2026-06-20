import Navbar from "@/components/landing/Navbar";
import Hero from "@/components/landing/Hero";
import LiveDemoPreview from "@/components/landing/LiveDemoPreview";
import FeaturesGrid from "@/components/landing/FeaturesGrid";
import HowItWorks from "@/components/landing/HowItWorks";
import FinalCTA from "@/components/landing/FinalCTA";
import Footer from "@/components/landing/Footer";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white selection:bg-indigo-100 selection:text-indigo-900 flex flex-col">
      <Navbar />
      <main className="flex-1">
        <Hero />
        <LiveDemoPreview />
        <FeaturesGrid />
        <HowItWorks />
        <FinalCTA />
      </main>
      <Footer />
    </div>
  );
}