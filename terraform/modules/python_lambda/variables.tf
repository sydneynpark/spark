variable "function_name" {
  type = string
}

variable "project_dir" {
  description = "The Lambda project directory, relative to the root module."
  type        = string
}

variable "role_name" {
  description = "Name of the function's execution role."
  type        = string
}

variable "role_path" {
  type    = string
  default = "/"
}

variable "role_description" {
  type    = string
  default = null
}

variable "permissions_boundary" {
  description = "ARN of the execution role's permissions boundary."
  type        = string
}

variable "policy" {
  description = "JSON policy document: what the function can do, besides writing its logs."
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

variable "log_retention_days" {
  type    = number
  default = 3
}
