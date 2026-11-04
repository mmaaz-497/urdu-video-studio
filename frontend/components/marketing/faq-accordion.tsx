'use client'

import { Reveal } from '@/components/marketing/reveal'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'

const FAQS = [
  {
    q: 'What does Urdu Video Studio do?',
    a: 'It turns a short idea into a finished video with an Urdu voice-over. You describe the idea, review the Urdu script we write, and approve it — then we generate the scenes, add the narration, and assemble the video.',
  },
  {
    q: 'Which languages can I use?',
    a: 'Write your idea in Roman Urdu (for example “bachon ko solar energy samjhao”) or in Urdu script. The script and narration are always in Urdu. The website itself is in English.',
  },
  {
    q: 'How long can my videos be?',
    a: 'You choose 5, 10 or 15 seconds. Short clips keep each video focused on a single idea and quick to generate.',
  },
  {
    q: 'Who is it for?',
    a: 'It is built for educational use — teachers, students and learners explaining a concept, a science experiment or a simple how-to in Urdu.',
  },
  {
    q: 'Can I edit the script before the video is made?',
    a: 'Yes. You always see the script first and can change the wording and approve it before any video is generated. If it is over the word limit for your chosen length, you will be asked to shorten it.',
  },
  {
    q: 'What if a video fails to generate?',
    a: 'It appears in My Videos marked as failed with a reason, and you can retry it from there. You can also delete any video you no longer need.',
  },
]

export function FaqAccordion() {
  return (
    <section id="faq" className="mx-auto max-w-3xl scroll-mt-20 px-4 pb-24 sm:px-6">
      <Reveal>
        <p className="text-body-sm font-semibold uppercase tracking-wider text-primary">FAQ</p>
        <h2 className="mt-2 text-h1 font-bold tracking-tight">Questions, answered</h2>
      </Reveal>
      <Reveal className="mt-8" delay={100}>
        <Accordion type="single" collapsible defaultValue="item-0" className="border-t border-border">
          {FAQS.map((faq, i) => (
            <AccordionItem key={faq.q} value={`item-${i}`}>
              <AccordionTrigger>{faq.q}</AccordionTrigger>
              <AccordionContent>{faq.a}</AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </Reveal>
    </section>
  )
}
