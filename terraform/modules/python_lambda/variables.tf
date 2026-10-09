variable "function_name" {
  type = string
}

variable "project_dir" {
  description = "The Lambda project directory, relative to the root module."
  type        = string
}

variable "role_arn" {
  description = "ARN of the function's execution role."
  type        = string
}

variable "handler" {
  type    = string
  default = "lambda_function.lambda_handler"
}

variable "description" {
  type    = string
  default = ""
}

variable "memory_size" {
  type    = number
  default = 128
}

variable "timeout" {
  description = "In seconds."
  type        = number
  default     = 3
}

variable "layers" {
  type    = list(string)
  default = []
}
