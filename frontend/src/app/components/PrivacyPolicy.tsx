export function PrivacyPolicy() {
  return (
    <div className="min-h-screen bg-white px-6 py-12 max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">Politica de Privacidad</h1>
      <p className="text-sm text-gray-500 mb-8">Ultima actualizacion: 2 de mayo de 2026</p>

      <div className="space-y-6 text-gray-700 text-sm leading-relaxed">
        <section>
          <h2 className="text-lg font-semibold text-gray-900 mb-2">1. Informacion que recopilamos</h2>
          <p>
            Fina recopila la siguiente informacion cuando usas nuestra aplicacion:
          </p>
          <ul className="list-disc pl-5 mt-2 space-y-1">
            <li>Nombre, apellido y direccion de email (al registrarte o iniciar sesion con Google)</li>
            <li>Datos financieros que ingresas voluntariamente: gastos, ingresos, categorias, presupuestos y comercios</li>
            <li>Acceso a tu casilla de Gmail (solo si lo autorizas explicitamente) para detectar notificaciones de gastos de tus bancos</li>
          </ul>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-gray-900 mb-2">2. Como usamos tu informacion</h2>
          <p>Usamos tu informacion exclusivamente para:</p>
          <ul className="list-disc pl-5 mt-2 space-y-1">
            <li>Proporcionarte el servicio de gestion de finanzas personales</li>
            <li>Categorizar automaticamente tus gastos</li>
            <li>Mostrarte resumenes y estadisticas de tus finanzas</li>
            <li>Enviarte notificaciones por WhatsApp sobre tus gastos (si lo autorizas)</li>
          </ul>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-gray-900 mb-2">3. Almacenamiento y seguridad</h2>
          <p>
            Tus datos se almacenan en servidores seguros de Microsoft Azure. Las contrasenas se encriptan
            con bcrypt y las sesiones se manejan con tokens JWT. No vendemos ni compartimos tus datos
            personales o financieros con terceros.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-gray-900 mb-2">4. Acceso a Gmail</h2>
          <p>
            Si autorizas el acceso a Gmail, Fina solo lee emails de notificaciones bancarias para
            registrar gastos automaticamente. No leemos, almacenamos ni compartimos ningun otro
            contenido de tu casilla de email.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-gray-900 mb-2">5. Tus derechos</h2>
          <p>Podes en cualquier momento:</p>
          <ul className="list-disc pl-5 mt-2 space-y-1">
            <li>Acceder a todos tus datos desde la aplicacion</li>
            <li>Eliminar tu cuenta y todos los datos asociados</li>
            <li>Revocar el acceso a Gmail desde la configuracion de tu cuenta de Google</li>
          </ul>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-gray-900 mb-2">6. Contacto</h2>
          <p>
            Si tenes preguntas sobre esta politica de privacidad, podes contactarnos
            en <a href="mailto:davor.vindis99@gmail.com" className="text-blue-600 underline">davor.vindis99@gmail.com</a>.
          </p>
        </section>
      </div>
    </div>
  );
}
