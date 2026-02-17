
export function Footer() {
    return (
        <footer className="border-t bg-slate-50">
            <div className="container mx-auto px-4 py-12">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
                    <div>
                        <h3 className="text-sm font-semibold text-slate-900 mb-4">Product</h3>
                        <ul className="space-y-2">
                            <li><a href="#" className="text-sm text-slate-600 hover:text-blue-600 transition-colors">Job Search</a></li>
                            <li><a href="#" className="text-sm text-slate-600 hover:text-blue-600 transition-colors">Post a Job</a></li>
                        </ul>
                    </div>
                    <div>
                        <h3 className="text-sm font-semibold text-slate-900 mb-4">Company</h3>
                        <ul className="space-y-2">
                            <li><a href="#" className="text-sm text-slate-600 hover:text-blue-600 transition-colors">About</a></li>
                            <li><a href="#" className="text-sm text-slate-600 hover:text-blue-600 transition-colors">Contact</a></li>
                        </ul>
                    </div>
                    <div>
                        <h3 className="text-sm font-semibold text-slate-900 mb-4">Legal</h3>
                        <ul className="space-y-2">
                            <li><a href="#" className="text-sm text-slate-600 hover:text-blue-600 transition-colors">Privacy Policy</a></li>
                            <li><a href="#" className="text-sm text-slate-600 hover:text-blue-600 transition-colors">Terms of Service</a></li>
                        </ul>
                    </div>
                </div>
                <div className="mt-12 pt-8 border-t border-slate-200">
                    <p className="text-center text-sm text-slate-500">
                        &copy; {new Date().getFullYear()} TechJobs Inc. All rights reserved.
                    </p>
                </div>
            </div>
        </footer>
    );
}
