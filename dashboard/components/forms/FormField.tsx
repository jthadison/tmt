import { useFormContext } from 'react-hook-form'
import { AlertCircle } from 'lucide-react'

interface FormFieldProps {
  name: string
  label: string
  type?: string
  placeholder?: string
  suggestion?: string
  exampleValue?: string
  className?: string
}

export function FormField({
  name,
  label,
  type = 'text',
  placeholder,
  suggestion,
  exampleValue,
  className = '',
}: FormFieldProps) {
  const { register, formState: { errors } } = useFormContext()
  const error = errors[name]

  return (
    <div className={`mb-4 ${className}`}>
      <label htmlFor={name} className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
        {label}
      </label>

      <input
        id={name}
        type={type}
        placeholder={placeholder}
        {...register(name)}
        className={`
          w-full px-3 py-2 border rounded-lg
          focus:outline-none focus:ring-2
          ${error
            ? 'border-red-500 focus:ring-red-500 focus:border-red-500'
            : 'border-gray-300 dark:border-gray-600 focus:ring-blue-500 focus:border-blue-500'
          }
          bg-white dark:bg-gray-800 text-gray-900 dark:text-white
        `}
      />

      {error && (
        <div className="mt-2 flex items-start gap-2 text-sm text-red-600 dark:text-red-400">
          <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
          <div>
            <p>{error.message as string}</p>
            {suggestion && (
              <p className="mt-1 text-red-500 dark:text-red-300">
                <strong>Suggestion:</strong> {suggestion}
              </p>
            )}
            {exampleValue && (
              <p className="mt-1 text-red-500 dark:text-red-300">
                <strong>Example:</strong> {exampleValue}
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
