import { createClient } from '@supabase/supabase-js'

const supabaseUrl = 'https://kvwtbupvcvyktgpsgnqu.supabase.co'
const supabaseAnonKey = 'sb_publishable_T6ZV8_g_QSMHbCd3xCkHZQ_wp463TtL'

export const supabase = createClient(supabaseUrl, supabaseAnonKey)
