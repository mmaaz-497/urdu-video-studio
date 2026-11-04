import { FaqAccordion } from '@/components/marketing/faq-accordion'
import { Hero } from '@/components/marketing/hero'
import { HowItWorks } from '@/components/marketing/how-it-works'
import { ShowcaseGrid } from '@/components/marketing/showcase-grid'
import { SiteFooter } from '@/components/marketing/site-footer'

export default function LandingPage() {
  return (
    <>
      <Hero />
      <HowItWorks />
      <ShowcaseGrid />
      <FaqAccordion />
      <SiteFooter />
    </>
  )
}
