import Header from '@/components/Header'
import Hero from '@/components/Hero'
import SocialProof from '@/components/SocialProof'
import FeatureSections from '@/components/FeatureSections'
import DesignedByExperts from '@/components/DesignedByExperts'
import GuidedPaths from '@/components/GuidedPaths'
import Footer from '@/components/Footer'

export default function Home() {
  return (
    <main className="min-h-screen">
      <Header />
      <Hero />
      <SocialProof />
      <FeatureSections />
      <DesignedByExperts />
      <GuidedPaths />
      <Footer />
    </main>
  )
}

