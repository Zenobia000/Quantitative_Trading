import { QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider } from 'react-router-dom'
import { I18nextProvider } from 'react-i18next'
import { queryClient } from '@/services/queryClient'
import { router } from '@/router'
import { ThemeProvider } from '@/app/theme'
import i18n from '@/i18n'
import { DocumentLang } from '@/components/DocumentLang'

export default function App() {
  return (
    <ThemeProvider>
      <I18nextProvider i18n={i18n}>
        <DocumentLang />
        <QueryClientProvider client={queryClient}>
          <RouterProvider router={router} />
        </QueryClientProvider>
      </I18nextProvider>
    </ThemeProvider>
  )
}
